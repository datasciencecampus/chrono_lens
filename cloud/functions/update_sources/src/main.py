import base64
import json
import logging
import os

from opentelemetry import trace

import dsc_lib.gcloud.logging
import dsc_lib.images.sources.tfl
from dsc_lib.error_handling import report_exception
from dsc_lib.gcloud.buckets import write_to_bucket

dsc_lib.gcloud.logging.setup_logging_and_trace()


def update_sources(event, context):
    """Triggered from a message on a Cloud Pub/Sub topic.
    Args:
         event (dict): Event payload.
         context (google.cloud.functions.Context): Metadata for the event.
    """

    tracer = trace.get_tracer(__name__)

    sources_bucket_name = None

    try:
        with tracer.start_as_current_span("update_sources"):

            if 'data' in event:
                pubsub_message = base64.b64decode(event['data']).decode('utf-8')
                logging.info(f'PubSub event: "{pubsub_message}"')

            sources_bucket_name = os.environ.get('SOURCES_BUCKET_NAME')

            with tracer.start_as_current_span('update TfL'):
                logging.info(f'Updating TfL image sources...')
                tfl_images_gc_destination = 'ingest/TfL-images.json'
                tfl_sources = dsc_lib.images.sources.tfl.download_urls()
                url_list = dsc_lib.images.sources.tfl.filter_image_urls(tfl_sources)
                write_to_bucket(sources_bucket_name, tfl_images_gc_destination, json.dumps(url_list))
                logging.info(f'...TfL image sources updated.')

    except Exception as e:
        return report_exception(e,
                                {'sources_bucket_name': sources_bucket_name},
                                event=event, context=context)
