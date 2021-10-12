import datetime
import json
import logging
import os
from typing import List

import google.cloud.storage
from dateutil.rrule import rrule, MINUTELY
from google.cloud import bigquery
from opentelemetry import trace

from chrono_lens.gcloud.async_functions import run_cloud_function_async_with_parameter_list
from chrono_lens.gcloud.bigquery import convert_model_name_to_table_name
from chrono_lens.gcloud.call_handling import extract_request_field
from chrono_lens.gcloud.error_handling import report_exception
from chrono_lens.gcloud.logging import setup_logging_and_trace

"""
Example JSON:
{
    "date_to_process": "20200519",
    "camera_id": "sd_durhamcouncil06",
    "data_root": "Durham-images",
    "model_blob_name": "NewcastleV0"
}
"""

setup_logging_and_trace()

gcp_region = os.environ.get('FUNCTION_REGION', '')  # Built-in env var
gcp_project = os.environ.get('GCP_PROJECT', '')  # Built-in env var

run_model_on_image_endpoint = f'https://{gcp_region}-{gcp_project}.cloudfunctions.net/run_model_on_image'
logging.info(f'Using run_model_on_image endpoint: "{run_model_on_image_endpoint}"')

bigquery_client = bigquery.Client()

DATASET_NAME = 'detected_objects'  # As defined in gcp-setup.sh (BigQuery dataset creation)

storage_client = google.cloud.storage.Client()
data_bucket_name = os.environ.get('DATA_BUCKET_NAME')  # Built-in env var
try:
    data_bucket = storage_client.get_bucket(data_bucket_name)
except google.cloud.exceptions.NotFound:
    data_bucket = None


def process_day(request):
    """Responds to any HTTP request.
    Args:
        request (flask.Request): HTTP request object.
    Returns:
        The response text or any set of values that can be turned into a
        Response object using
        `make_response <http://flask.pocoo.org/docs/1.0/api/#flask.Flask.make_response>`.
    """
    tracer = trace.get_tracer(__name__)

    date_to_process_raw = None
    camera_id = None
    data_root = None
    model_blob_name = None

    try:
        with tracer.start_as_current_span("process_day"):
            if data_bucket_name is None:
                raise RuntimeError('"DATA_BUCKET_NAME" not defined as an environment variable')

            if data_bucket is None:
                raise RuntimeError(f'Google bucket name "{data_bucket_name}" (used for "data_bucket_name")'
                                   ' failed to open a bucket')

            date_to_process_raw = extract_request_field(request, 'date_to_process')
            try:
                date_to_process = datetime.datetime.strptime(date_to_process_raw, '%Y%m%d')
            except ValueError as ve:
                message = f'"date_to_process" incorrect format (received "{date_to_process_raw}", expected "YYYYMMDD")'
                logging.critical(f'ERROR: function aborted - {message}')
                raise ValueError(message) from ve

            camera_id = extract_request_field(request, 'camera_id')
            data_root = extract_request_field(request, 'data_root')
            model_blob_name = extract_request_field(request, 'model_blob_name')

            with tracer.start_as_current_span('Discovering images in bucket'):
                data_blobs = list(storage_client.list_blobs(data_bucket, max_results=1, prefix=data_root))
                if len(data_blobs) == 0:
                    raise ValueError(f'"{data_root}" does not exist within bucket "{data_bucket_name}"')

                data_blobs = list(
                    storage_client.list_blobs(data_bucket, max_results=1, prefix=f'{data_root}/{date_to_process_raw}'))
                if len(data_blobs) == 0:
                    raise ValueError(
                        f'"{data_root}" does not have "{date_to_process_raw}" present within bucket "{data_bucket_name}"')

            sample_times = [f'{sample_time:%H%M}' for sample_time
                            in rrule(dtstart=date_to_process, count=24 * 6, interval=10, freq=MINUTELY)]

            processed_times = identify_processed_times(
                date_to_process=date_to_process,
                camera_id=camera_id,
                data_root=data_root,
                model_blob_name=model_blob_name
            )
            logging.debug(f'Skipping already processed times: {processed_times}')

            sample_times_to_process = [sample_time for sample_time in sample_times if
                                       sample_time not in processed_times]

            data_urls = [f'{data_root}/{date_to_process_raw}/{sample_time}/{camera_id}.jpg' for sample_time in
                         sample_times_to_process]

            results = {
                'STATUS': 'OK',
                'Counts': {
                    'Already Processed': len(processed_times)
                }
            }

            if len(data_urls) > 0:
                with tracer.start_as_current_span('CF call: run_model_on_image'):
                    asyncio_results = run_cloud_function_async_with_parameter_list(
                        'data_blob_name', data_urls,
                        {'model_blob_name': model_blob_name},
                        run_model_on_image_endpoint)

                    for result, data_url in zip(asyncio_results, data_urls):
                        result_type = result['STATUS']
                        results['Counts'][result_type] = results['Counts'].get(result_type, 0) + 1

                        if result['STATUS'] == 'Errored':
                            logging.critical(f'Incomplete execution - possible outage; "{data_url}" result: {result}')

                        elif result['STATUS'] not in ['Processed', 'Faulty', 'Missing']:
                            logging.error(f'Unexpected STATUS type: "{result["STATUS"]}"')
                            logging.info(f'Full received result: "{result}"')

            return json.dumps(results)

    except Exception as e:
        return report_exception(e,
                                {'date_to_process_raw': date_to_process_raw,
                                 'camera_id': camera_id,
                                 'data_root': data_root,
                                 'model_blob_name': model_blob_name},
                                request=request)


def identify_processed_times(model_blob_name: str, date_to_process: datetime, camera_id: str,
                             data_root: str) -> List[str]:
    model_name = convert_model_name_to_table_name(model_blob_name)

    table_names_list = [table_obj.table_id for table_obj in bigquery_client.list_tables(DATASET_NAME)]
    if model_name not in table_names_list:
        return []

    table_id = ".".join([gcp_project, DATASET_NAME, model_name])

    query = f"""
        SELECT time
        FROM `{table_id}`
        WHERE source="{data_root}"
            AND camera_id="{camera_id}"
            AND date="{date_to_process:%Y-%m-%d}"
    """
    query_job = bigquery_client.query(query)  # Make an API request.

    rows = query_job.result()
    logging.debug(f'Processed {query_job.total_bytes_processed} bytes')

    processed_times = []
    for row in rows:
        # Row values can be accessed by field name or index.
        processed_times.append(f'{row["time"]:%H%M}')

    processed_times_without_duplicates = set(processed_times)
    processed_times_without_duplicates_list_form = list(processed_times_without_duplicates)
    processed_times_without_duplicates_list_form.sort()

    return processed_times_without_duplicates_list_form
