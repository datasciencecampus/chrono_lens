import json
import logging
import os
from datetime import datetime, timedelta

import google.cloud.storage
from opentelemetry import trace

from dsc_lib.error_handling import report_exception
from dsc_lib.gcloud.async_functions import run_cloud_function_async_with_parameter_list
from dsc_lib.gcloud.buckets import read_from_bucket
from dsc_lib.gcloud.logging import setup_logging_and_trace

setup_logging_and_trace()

gcp_region = os.environ.get('FUNCTION_REGION', '')  # Built-in env var
gcp_project = os.environ.get('GCP_PROJECT', '')  # Built-in env var
run_model_on_image_endpoint = f'https://{gcp_region}-{gcp_project}.cloudfunctions.net/run_model_on_image'

logging.info(f'Using run_model_on_image_endpoint: "{run_model_on_image_endpoint}"')

BLOB_PREFIX = 'analyse'
DATA_BATCH_SIZE = 400


def process_scheduled(event, context):
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
        with tracer.start_as_current_span("process_scheduled"):
            sources_bucket_name = os.environ.get('SOURCES_BUCKET_NAME')
            if sources_bucket_name is None:
                raise RuntimeError('"SOURCES_BUCKET_NAME" not defined as an environment variable')

            storage_client = google.cloud.storage.Client()

            now = datetime.now()
            twenty_minutes_ago = now - timedelta(minutes=20)
            twenty_minutes_ago = twenty_minutes_ago - timedelta(minutes=twenty_minutes_ago.minute % 10,
                                                                seconds=twenty_minutes_ago.second,
                                                                microseconds=twenty_minutes_ago.microsecond)
            logging.info(f'Processing data on {twenty_minutes_ago:%Y%m%d}/{twenty_minutes_ago:%H%M}')

            model_configuration_blob_name = f'{BLOB_PREFIX}-configuration.json'
            logging.info(f'Pulling model configuration from "{sources_bucket_name}/{model_configuration_blob_name}"')
            with tracer.start_as_current_span("read model configuration"):
                model_configuration_json = read_from_bucket(sources_bucket_name, model_configuration_blob_name,
                                                            client=storage_client)
                model_configuration = json.loads(model_configuration_json)
                logging.debug(f'Model configuration: "{model_configuration}"')

            logging.info(f'Searching bucket {sources_bucket_name}/{BLOB_PREFIX} for JSON files...')
            with tracer.start_as_current_span("Search sources bucket for JSON"):
                blobs = storage_client.list_blobs(sources_bucket_name, prefix=BLOB_PREFIX + '/')
                data_blob_names = []
                for blob in blobs:
                    if blob.name.endswith(".json"):
                        logging.debug(f'=>  Reading URLs from {blob.name}')
                        json_data = blob.download_as_string()
                        camera_ids = json.loads(json_data)

                        data_json_name = os.path.basename(blob.name)
                        data_root = os.path.splitext(data_json_name)[0]

                        for camera_id in camera_ids:
                            data_blob_names.append(
                                f'{data_root}/{twenty_minutes_ago:%Y%m%d}/{twenty_minutes_ago:%H%M}/{camera_id}.jpg')

            logging.info(f'...search in bucket {sources_bucket_name}/{BLOB_PREFIX} for JSON files complete.')

            results = {
                'STATUS': 'OK',
                'Counts': {}
            }

            with tracer.start_as_current_span("CF call run_model_on_image"):
                data_blob_batches = [data_blob_names[x:x + DATA_BATCH_SIZE]
                                     for x in range(0, len(data_blob_names), DATA_BATCH_SIZE)]
                for data_blob_batch in data_blob_batches:
                    asyncio_results = run_cloud_function_async_with_parameter_list(
                        json_key='data_blob_name', json_values=data_blob_batch,
                        partial_json={'model_blob_name': model_configuration['model_blob_name']},
                        endpoint=run_model_on_image_endpoint
                    )

                    for result, json_value in zip(asyncio_results, data_blob_batch):
                        result_type = result['STATUS']
                        results['Counts'][result_type] = results['Counts'].get(result_type, 0) + 1

                        if result['STATUS'] == 'Errored':
                            logging.critical(f'Incomplete execution - possible outage: "{json_value}" result: {result}')

                        elif result['STATUS'] not in ['Processed', 'Faulty', 'Missing']:
                            logging.error(f'Unexpected STATUS type: "{result["STATUS"]}"')
                            logging.info(f'Full received result: "{result}"')

            logging.info(f'Results: {results}')

            return json.dumps(results)

    except Exception as e:
        return report_exception(e,
                                {'sources_bucket_name': sources_bucket_name},
                                event=event, context=context)
