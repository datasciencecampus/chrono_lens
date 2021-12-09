import base64
import json
import logging
import os

from opentelemetry import trace

import chrono_lens.gcloud.logging
import chrono_lens.images.sources.tfl
from chrono_lens.gcloud.buckets import write_to_bucket
from chrono_lens.gcloud.error_handling import report_exception

chrono_lens.gcloud.logging.setup_logging_and_trace()


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
                tfl_sources = chrono_lens.images.sources.tfl.download_urls()
                url_list = chrono_lens.images.sources.tfl.filter_image_urls(tfl_sources)
                write_to_bucket(sources_bucket_name, tfl_images_gc_destination, json.dumps(url_list))
                logging.info(f'...TfL image sources updated.')

    except Exception as e:
        return report_exception(e,
                                {'sources_bucket_name': sources_bucket_name},
                                event=event, context=context)
