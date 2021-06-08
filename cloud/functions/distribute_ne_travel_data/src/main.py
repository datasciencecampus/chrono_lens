import asyncio
import json
import logging
import os
import urllib.error
from datetime import datetime, timedelta
from random import uniform
from time import sleep
from urllib.request import urlopen

import aiohttp
import dateutil.parser
import google.cloud.storage
import pytz
from opentelemetry import trace

from dsc_lib.error_handling import report_exception
from dsc_lib.gcloud.logging import setup_logging_and_trace
from dsc_lib.images.correction import resize_jpeg_image, IMAGE_MAX_AXIS_THRESHOLD

setup_logging_and_trace()

MAXIMUM_NUMBER_OF_ATTEMPTS = 5
SLEEP_MINIMUM = 2
SLEEP_MAXIMUM = 10

data_bucket_name = os.environ.get('DATA_BUCKET_NAME')

storage_client = google.cloud.storage.Client()

try:
    data_storage_bucket = storage_client.get_bucket(data_bucket_name)
except google.cloud.exceptions.NotFound:
    data_storage_bucket = None


def distribute_ne_travel_data(event, context):
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

    try:
        with tracer.start_as_current_span("distribute_ne_travel_data"):
            if data_bucket_name is None:
                raise RuntimeError('"DATA_BUCKET_NAME" not defined as an environment variable')

            if data_storage_bucket is None:
                raise RuntimeError(f'Google bucket name "{data_bucket_name}" (used for "data_bucket_name")'
                                   ' failed to open a bucket')

            utc = pytz.UTC
            now = utc.localize(datetime.utcnow())
            now = now - timedelta(minutes=now.minute % 10, seconds=now.second, microseconds=now.microsecond)
            ten_minutes_ago = now - timedelta(minutes=10)

            with tracer.start_as_current_span("Searching for updates"):
                logging.debug('Sifting latest camera images...')
                name_url_tuples = sift_newcastle_cameras_latest_newer_than_datetime(ten_minutes_ago)
                logging.debug(f'...found {len(name_url_tuples)} camera images updated in the last 10 minutes.')

            with tracer.start_as_current_span("Downloading updated images"):
                logging.debug('Downloading nearest timed images...')
                base_blob_name = f'NETravelData-images/{now:%Y%m%d/%H%M}/'
                asyncio.run(run_async_downloads(name_url_tuples, base_blob_name))
                logging.debug(f'...done.')

            # We're not returning to anyone, so no results to return...
            return

    except Exception as e:
        return report_exception(e,
                                {'data_bucket_name': data_bucket_name},
                                event=event, context=context)


def sift_newcastle_cameras_latest_newer_than_datetime(threshold_datetime):
    page_number = 1
    name_url_tuples = []
    while True:
        newcastle_api_url = "https://api.newcastle.urbanobservatory.ac.uk/api/v2/sensors/entity/?metric=%22Camera%20" \
            f"image%22&page={page_number}"

        remaining_attempts = 5
        newcastle_api_raw_response = None
        while newcastle_api_raw_response is None and remaining_attempts > 0:
            try:
                newcastle_api_raw_response = urlopen(newcastle_api_url)
                logging.debug(f'Loaded page {page_number} with {remaining_attempts} retries remaining')
            except urllib.error.HTTPError as e:
                logging.debug(f'Exception: {e}; {remaining_attempts} retries remaining')
                sleep(5 + uniform(0, 5))

                remaining_attempts -= 1
                if remaining_attempts == 0:
                    raise e

        newcastle_api_response = json.load(newcastle_api_raw_response)

        for item in newcastle_api_response["items"]:
            for feed in item["feed"]:
                if len(feed["timeseries"]) > 1:
                    raise ValueError(f'Expecting 1 entry in timeseries for "{item["name"]}",'
                                     f' found {len(feed["timeseries"])}')

                timeseries = feed["timeseries"][0]
                if "latest" in timeseries:
                    image_datetime_raw = timeseries["latest"]["time"]
                    image_datetime = dateutil.parser.isoparse(image_datetime_raw)
                    if image_datetime > threshold_datetime:
                        if len(feed["brokerage"]) > 1:
                            raise ValueError(f'Expecting 1 entry in brokerage for "{item["name"]}",'
                                             f' found {len(feed["brokerage"])}')

                        image_url = timeseries["latest"]["value"]
                        camera_name = feed["brokerage"][0]["sourceId"]
                        if ":" in camera_name:
                            original_camera_name = camera_name
                            camera_name, view_name = original_camera_name.split(":")
                            camera_name += "-View_" + view_name[1:]
                        name_url_tuples.append((camera_name, image_url))

        page_number += 1

        if page_number > newcastle_api_response["pagination"]["pageCount"]:
            break

    return name_url_tuples


async def run_async_downloads(name_url_tuples, base_blob_name):
    async with aiohttp.ClientSession() as session:
        return await asyncio.gather(
            *(async_download_to_blob(name_url_tuple, session, base_blob_name)
              for name_url_tuple in name_url_tuples)
        )


async def async_download_to_blob(name_url_tuple, session, base_blob_name):
    # @todo not unit tested
    blob_name = base_blob_name + name_url_tuple[0] + ".jpg"
    image_url = name_url_tuple[1]
    logging.debug(f'Downloading: "{image_url}" to "{blob_name}"...')

    for attempt_number in range(MAXIMUM_NUMBER_OF_ATTEMPTS):

        response = await session.get(image_url, ssl=False)

        async with response:
            data_content = await response.content.read()

            if response.status == 200:

                resized_jpeg_image = resize_jpeg_image(data_content, IMAGE_MAX_AXIS_THRESHOLD)

                if resized_jpeg_image is None:
                    logging.warning(f'Failed to decode URL="{image_url}"  - empty bitmap generated')

                else:
                    blob = data_storage_bucket.blob(blob_name)
                    blob.upload_from_string(resized_jpeg_image, content_type='image/jpeg')
                    logging.debug(f'...downloaded "{image_url}" to "{blob_name}"')

                return

            elif response.status == 401 or response.status == 403:
                # No point retrying if error is permission denied or similar security issue
                logging.error(f'Forbidden - not authorised on attempt#{attempt_number}, not retrying:'
                              f' code={response.status}, url="{image_url}"')
                return

            logging.debug(f'Failed attempt#{attempt_number}: code={response.status}: "{image_url}";')

            # No need to wait after the last attempt, we've given up now - so don't waste compute cycles
            if attempt_number < MAXIMUM_NUMBER_OF_ATTEMPTS - 1:
                await asyncio.sleep(uniform(SLEEP_MINIMUM, SLEEP_MAXIMUM))
                # sleep(uniform(SLEEP_MINIMUM, SLEEP_MAXIMUM))

    logging.error(f'Failed after {MAXIMUM_NUMBER_OF_ATTEMPTS} attempts with "{image_url}"')
