import json
import logging
import os
from datetime import datetime, timedelta

from google.cloud import storage
from opentelemetry import trace

from dsc_lib.error_handling import report_exception
from dsc_lib.gcloud.async_functions import run_cloud_function_async_with_parameter_list
from dsc_lib.gcloud.logging import setup_logging_and_trace

setup_logging_and_trace()

gcp_region = os.environ.get('FUNCTION_REGION', '')  # Built-in env var
gcp_project = os.environ.get('GCP_PROJECT', '')  # Built-in env var
distribute_uris_endpoint = f'https://{gcp_region}-{gcp_project}.cloudfunctions.net/distribute_uri_sources'

logging.info(f'Using distribute_uris_endpoint: "{distribute_uris_endpoint}"')


def distribute_json_sources(event, context):
    """Background Cloud Function to be triggered by Pub/Sub.
    Args:
         event (dict):  The dictionary with data specific to this type of
         event. The `data` field contains the PubsubMessage message. The
         `attributes` field will contain custom attributes if there are any.

         context (google.cloud.functions.Context): The Cloud Functions event
         metadata. The `event_id` field contains the Pub/Sub message ID. The
         `timestamp` field contains the publish time.
    """
    tracer = trace.get_tracer(__name__)

    sources_bucket_name = None

    try:
        with tracer.start_as_current_span("distribute_json_sources"):
            # Will throw if not present - and hence get logged
            sources_bucket_name = os.environ.get('SOURCES_BUCKET_NAME')

            now = datetime.now()
            now = now - timedelta(minutes=now.minute % 10, seconds=now.second, microseconds=now.microsecond)
            date_time_folder = f'{now:%Y%m%d}/{now:%H%M}'

            with tracer.start_as_current_span("Searching bucket for JSON"):
                logging.debug(f'Searching bucket {sources_bucket_name} for JSON files...')

                client = storage.Client()
                blobs = client.list_blobs(sources_bucket_name, prefix='ingest/')
                json_blob_names = []
                for blob in blobs:
                    if blob.name.endswith(".json"):
                        logging.debug(f'=>  Reading URLs from {blob.name}')
                        json_blob_names.append(blob.name)

                logging.debug(f'...search in bucket {sources_bucket_name} for JSON files complete.')

            with tracer.start_as_current_span("CF call distribute_uris"):
                asyncio_results = run_cloud_function_async_with_parameter_list(
                    'json_blob_name', json_blob_names,
                    {'date_time_folder': date_time_folder},
                    distribute_uris_endpoint,
                    sleep_base=0,
                    sleep_tuple=(0, 6)
                )

            results = {
                'STATUS': 'OK',
                'Counts': {}
            }
            for result, json_blob_name in zip(asyncio_results, json_blob_names):
                if 'Counts' in result:
                    for count_type in result['Counts']:
                        results['Counts'][count_type] = results['Counts'].get(count_type, 0) + result['Counts'][
                            count_type]
                else:
                    if result['STATUS'] == 'Errored':
                        logging.critical(f'Incomplete execution - possible outage;'
                                         f' "{json_blob_name}" results: {result}')
                    else:
                        logging.error(f"Unexpected STATUS type; result: {result}")

            logging.info(f'Results: {results}')

            return json.dumps(results)

    except Exception as e:
        return report_exception(e,
                                {'sources_bucket_name': sources_bucket_name},
                                event=event, context=context)
