import json
import logging
import os.path
from random import uniform
from time import sleep
from urllib.parse import urlparse

import requests
from opentelemetry import trace
from requests.exceptions import ConnectionError

from chrono_lens.gcloud.buckets import write_to_bucket
from chrono_lens.gcloud.call_handling import extract_request_field
from chrono_lens.gcloud.error_handling import report_exception
from chrono_lens.gcloud.logging import setup_logging_and_trace
from chrono_lens.images.correction import resize_jpeg_image, IMAGE_MAX_AXIS_THRESHOLD

#
# Example triggering JSON:
#
# {
#   "file_url": "https:/somewebsite.org/somefile.txt",
#   "destination_bucket_url" : "gs://data-testproject-branch/test1"
# }
#

setup_logging_and_trace()

MAXIMUM_NUMBER_OF_ATTEMPTS = 5
SLEEP_BASE = 16
SLEEP_TUPLE = (1, 16)


def download_file(request):
    """Downloads the given file, downsamples it and stores it in the named data bucket; assumes JPEG format image

    Enforces images downsampling at source, by downloading full resolution image, downsampling it if larger than
    threshold size defined in dsc_lib.images.correction.IMAGE_MAX_AXIS_THRESHOLD

    Args:
        request (flask.Request): HTTP request object.
    Returns:
        The response text or any set of values that can be turned into a
        Response object using
        `make_response <http://flask.pocoo.org/docs/1.0/api/#flask.Flask.make_response>`.
    """
    tracer = trace.get_tracer(__name__)

    file_url = None
    destination_blob_name = None
    data_bucket_name = None

    try:
        with tracer.start_as_current_span("download_file"):
            data_bucket_name = os.environ.get('DATA_BUCKET_NAME')

            file_url = extract_request_field(request, 'file_url')
            destination_blob_name = extract_request_field(request, 'destination_blob_name')

            parsed_file_url = urlparse(file_url)
            base_file_name = os.path.basename(parsed_file_url.path[1:])
            full_blob_name = destination_blob_name + '/' + base_file_name
            logging.info(f'Downloading "{file_url}" into gs://{data_bucket_name}/{full_blob_name}')

            response = None

            with tracer.start_as_current_span("Downloading file"):
                for attempt_number in range(MAXIMUM_NUMBER_OF_ATTEMPTS):
                    try:
                        response = requests.get(file_url)

                        if response.status_code == 200 or response.status_code == 404:
                            break

                        logging.debug(
                            f'Failed attempt#{attempt_number}: code={response.status_code} with file_url="{file_url}";')

                    except ConnectionError as re:
                        logging.debug(f'Failed attempt#{attempt_number}: requests.get errored with "{re}"')

                    # No need to wait after the last attempt, we've given up now - so don't waste compute cycles
                    if attempt_number < MAXIMUM_NUMBER_OF_ATTEMPTS - 1:
                        sleep(SLEEP_BASE + uniform(*SLEEP_TUPLE))

                if response.status_code == 404:
                    file_missing_message = f'Failed to access URL="{file_url}" with error code #404 (file not found)'
                    logging.warning(file_missing_message)
                    return json.dumps({
                        'STATUS': 'Errored',
                        'Message': file_missing_message,
                        'Arguments': {'file_url': file_url,
                                      'destination_blob_name': destination_blob_name,
                                      'data_bucket_name': data_bucket_name}
                    })

                elif response.status_code != 200:
                    raise RuntimeError(f'Failed to access URL="{file_url}" with error code #{response.status_code}')

            resized_jpeg_image = resize_jpeg_image(response.content, IMAGE_MAX_AXIS_THRESHOLD)

            if resized_jpeg_image is None:
                decode_failure_message = f'Failed to decode URL="{file_url}"  - empty bitmap generated'
                logging.warning(decode_failure_message)
                return json.dumps({
                    'STATUS': 'Errored',
                    'Message': decode_failure_message,
                    'Arguments': {'file_url': file_url,
                                  'destination_blob_name': destination_blob_name,
                                  'data_bucket_name': data_bucket_name}
                })

            else:
                with tracer.start_as_current_span("Storing file"):
                    write_to_bucket(data_bucket_name, full_blob_name, resized_jpeg_image, content_type='image/jpeg')

                return json.dumps({'STATUS': 'OK'})

    except Exception as e:
        return report_exception(e,
                                {'file_url': file_url,
                                 'destination_blob_name': destination_blob_name,
                                 'data_bucket_name': data_bucket_name},
                                request=request)
