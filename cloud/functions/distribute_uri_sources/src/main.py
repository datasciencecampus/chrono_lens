import json
import logging
import os

from opentelemetry import trace
from opentelemetry.trace import Link

from dsc_lib.call_handling import extract_request_field
from dsc_lib.error_handling import report_exception
from dsc_lib.gcloud.async_functions import run_cloud_function_async_with_parameter_list
from dsc_lib.gcloud.buckets import read_from_bucket
from dsc_lib.gcloud.logging import setup_logging_and_trace

#
# Example JSON trigger:
#
# {
# "json_blob_name": "ingest/mycameras.json",
# "date_time_folder": "20200409/2143"
# }


setup_logging_and_trace()

gcp_region = os.environ.get('FUNCTION_REGION', '')  # Built-in env var
gcp_project = os.environ.get('GCP_PROJECT', '')  # Built-in env var
download_file_endpoint = f'https://{gcp_region}-{gcp_project}.cloudfunctions.net/download_file'

logging.info(f'Using download_file_endpoint: "{download_file_endpoint}"')


def distribute_uri_sources(request):
    """Responds to any HTTP request.
    Args:
        request (flask.Request): HTTP request object.
    Returns:
        The response text or any set of values that can be turned into a
        Response object using
        `make_response <http://flask.pocoo.org/docs/1.0/api/#flask.Flask.make_response>`.
    """
    tracer = trace.get_tracer(__name__)

    sources_bucket_name = None
    json_blob_name = None
    date_time_folder = None

    try:
        with tracer.start_as_current_span("distribute_uri_sources") as distribute_uri_sources:
            # Will throw if not present - and hence get logged
            sources_bucket_name = os.environ.get('SOURCES_BUCKET_NAME')

            json_blob_name = extract_request_field(request, 'json_blob_name')
            date_time_folder = extract_request_field(request, 'date_time_folder')

            logging.debug(f'Processing files from {json_blob_name}...')

            with tracer.start_as_current_span('Reading JSON from bucket',
                                              links=[Link(distribute_uri_sources.context)]):
                json_url_list = read_from_bucket(sources_bucket_name, json_blob_name)
                file_urls = json.loads(json_url_list)
                logging.debug(f'=>  Read {len(file_urls)} URLs from {json_blob_name}')

            base_json_name = os.path.basename(json_blob_name)
            base_name = os.path.splitext(base_json_name)[0]
            destination_blob_name = f'{base_name}/{date_time_folder}'
            logging.debug(f'Downloading {len(file_urls)} files to {destination_blob_name}')
            with tracer.start_as_current_span('CF call download_file',
                                              links=[Link(distribute_uri_sources.context)]):
                asyncio_results = run_cloud_function_async_with_parameter_list(
                    'file_url', file_urls,
                    {'destination_blob_name': destination_blob_name},
                    download_file_endpoint,
                    sleep_base=0,
                    sleep_tuple=(0, 6)
                )

            logging.debug(f'...processing files from {json_blob_name} complete.')

            results = {
                'STATUS': 'OK',
                'Counts': {}
            }
            for result in asyncio_results:
                result_type = result['STATUS']
                results['Counts'][result_type] = results['Counts'].get(result_type, 0) + 1

            return json.dumps(results)

    except Exception as e:
        return report_exception(e,
                                {'json_blob_name': json_blob_name,
                                 'sources_bucket_name': sources_bucket_name,
                                 'date_time_folder': date_time_folder},
                                request=request)
