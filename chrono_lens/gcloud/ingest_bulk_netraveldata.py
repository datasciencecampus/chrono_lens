import datetime
import json
import logging
import os
from time import sleep
from urllib.error import HTTPError
from urllib.request import urlopen

import requests
from google.api_core.exceptions import GoogleAPICallError
from google.cloud import storage, bigquery
from tqdm import tqdm

from chrono_lens.images.correction import resize_jpeg_image, IMAGE_MAX_AXIS_THRESHOLD


def round_time_up(dt, date_delta=datetime.timedelta(minutes=1)):
    """
    Round a datetime object to a multiple of a timedelta
    dt : datetime.datetime object, default now.
    dateDelta : timedelta object, we round to a multiple of this, default 1 minute.
    from:  http://stackoverflow.com/questions/3463930/how-to-round-the-minute-of-a-datetime-object-python
    """
    round_to = date_delta.total_seconds()
    seconds = (dt - dt.min).seconds

    if seconds % round_to == 0 and dt.microsecond == 0:
        rounding = (seconds + round_to / 2) // round_to * round_to
    else:
        # // is a floor division, not a comment on following line (like in javascript):
        rounding = (seconds + dt.microsecond / 1000000 + round_to) // round_to * round_to

    return dt + datetime.timedelta(0, rounding - seconds, - dt.microsecond)


def get_camera_address_from_utmc(utmc_id):
    api_base = 'https://api.newcastle.urbanobservatory.ac.uk/api/v2/sensors/'
    end_point = api_base + "entity?metric='Camera%20image'&brokerage:sourceId=" + utmc_id

    json_resp = None
    try:
        json_resp = urlopen(end_point)
    except HTTPError:
        for attempt_number in range(5):
            logging.info(f'Failed accessing UTMC "{end_point}"; retrying...')
            sleep(5)
            try:
                json_resp = urlopen(end_point)
                break
            except HTTPError:
                pass

    if json_resp is None:
        logging.warning(f'Failed to get camera address for UTMC ID {utmc_id}')
        return None

    resp = json.load(json_resp)

    entity_list = resp['items']
    for entity in entity_list:
        for link in entity['links']:
            if link['rel'] == "self.friendly":
                return link['href']

    return None


def get_views_for_camera(camera_iri):
    link_rel = 'self.friendly'

    camera_raw_json = None
    try:
        camera_raw_json = urlopen(camera_iri)
    except HTTPError:
        for attempt_number in range(5):
            logging.info(f'Failed accessing "{camera_iri}"; retrying...')
            sleep(5)
            try:
                camera_raw_json = urlopen(camera_iri)
                break
            except HTTPError:
                pass

    if camera_raw_json is None:
        logging.warning(f'Failed to open views for camera: "{camera_iri}"')
        return []

    camera = json.load(camera_raw_json)
    feeds = camera['feed']
    feeds_views_links = []
    for feed in feeds:
        name = feed['metric']
        view_id = feed['meta'].get('view_id', -1)

        view_iri = False
        for link in feed['links']:
            if link['rel'] == link_rel:
                view_iri = link['href']
                break

        ts_iri = False
        for link in feed['timeseries'][0]['links']:
            if link['rel'] == link_rel:
                ts_iri = link['href']
                break

        arch_iri = False
        for link in feed['timeseries'][0]['links']:
            if link['rel'] == 'archives.friendly':
                arch_iri = link['href']
                break

        feeds_views_links.append(
            {'name': name, 'view': view_id, 'default': feed['meta'].get('view_id', camera_iri), 'view_iri': view_iri,
             'timeseries': ts_iri, 'archiveIri': arch_iri})

    return feeds_views_links


def get_images_from_archive(archive_uri, start_time, end_time):
    end_point = archive_uri + '?startTime=' + start_time + '&endTime=' + end_time
    archive_raw_json = None
    try:
        archive_raw_json = urlopen(end_point)
    except HTTPError:
        for attempt_number in range(5):
            logging.info(f'Failed accessing image archive end point "{end_point}"; retrying...')
            sleep(5)
            try:
                archive_raw_json = urlopen(end_point)
                break
            except HTTPError:
                pass

    if archive_raw_json is None:
        logging.warning(f'Failed to open image archive end point: "{end_point}"')
        return []

    archive = json.load(archive_raw_json)
    historic = archive['historic']
    image_urls = [h['value'] for h in historic['values']]
    return image_urls


def download_data(file_url):
    response = requests.get(file_url)
    return response.content


def upload_images(image_urls, view_name, image_stats, bucket):
    if view_name == 'Camera_image':
        view_name = None

    blob_names_to_urls_with_time_mismatch = {}
    for image_url in image_urls:
        path = os.path.normpath(image_url)
        path = path.split(os.sep)

        camera_name = path[-3]
        if view_name:
            camera_name += '-' + view_name

        view_datetime = datetime.datetime(
            year=int(path[-2][:4]), month=int(path[-2][4:6]), day=int(path[-2][6:]),
            hour=int(path[-1][:2]), minute=int(path[-1][2:4]), second=int(path[-1][4:6]))

        view_rounded_datetime = round_time_up(view_datetime, date_delta=datetime.timedelta(minutes=10))

        view_datetime_diff = view_rounded_datetime - view_datetime
        blob_name = f'NETravelData-images/{view_rounded_datetime:%Y%m%d/%H%M}/{camera_name}.jpg'

        if blob_name not in blob_names_to_urls_with_time_mismatch:
            blob_names_to_urls_with_time_mismatch[blob_name] = (image_url, view_datetime_diff)
        else:
            if view_datetime_diff < blob_names_to_urls_with_time_mismatch[blob_name][1]:
                blob_names_to_urls_with_time_mismatch[blob_name] = (image_url, view_datetime_diff)

    for blob_name in blob_names_to_urls_with_time_mismatch:
        blob = bucket.blob(blob_name)

        blob_exists = None
        for attempt_number in range(5):
            try:
                blob_exists = blob.exists()
                break
            except GoogleAPICallError as ge:
                logging.info(f"Failed to access blob {blob_name} on attempt #{attempt_number}: {ge}")
                sleep(5)

        if blob_exists:
            image_stats['blobs_already_present'] += 1
            continue

        if blob_exists is None:
            logging.warning(f"Failed to get a response from bucket with blob {blob_name}, attempting upload anyway")

        file_url = blob_names_to_urls_with_time_mismatch[blob_name][0]
        image_data = download_data(file_url)

        resized_jpeg_image = resize_jpeg_image(image_data, IMAGE_MAX_AXIS_THRESHOLD)

        if resized_jpeg_image is None:
            logging.warning(f'Failed to decode URL="{file_url}"  - empty bitmap generated')

        else:
            blob.upload_from_string(resized_jpeg_image, content_type='image/jpeg')
            image_stats['patched_missing_image'] += 1


def upload_camera_images(camera_json, date_time, json_key_path, gcp_project):
    client = storage.Client.from_service_account_json(json_key_path)
    bucket_name = "data-" + gcp_project
    bucket = client.get_bucket(bucket_name)

    start_date_time = (date_time - datetime.timedelta(minutes=10)).isoformat()
    end_date_time = (date_time + datetime.timedelta(hours=23, minutes=50)).isoformat()

    image_stats = {
        'blobs_already_present': 0,
        'patched_missing_image': 0,
        'failed_to_check_blob': 0,
        'failed_to_download_archive': 0
    }

    for camera in tqdm(camera_json, desc='Pulling cameras', unit='camera', leave=False):
        camera_name = camera['systemCodeNumber']
        camera_uri = get_camera_address_from_utmc(camera_name)
        camera_views = get_views_for_camera(camera_uri)
        for camera_view in camera_views:  # tqdm(camera_views, desc='View per camera', unit='view', leave=False):
            if 'View' in camera_view['name'] or (
                    'View' not in camera_view['name'] and 'Camera image' in camera_view['name']):
                #  Note - may be >1 view per camera...
                view_name = camera_view['name'].replace('Camera image: ', '').replace(' ', '_')
                image_urls = get_images_from_archive(
                    archive_uri=camera_view['archiveIri'],
                    start_time=start_date_time,
                    end_time=end_date_time)
                upload_images(image_urls, view_name, image_stats, bucket)

    print(f'(present={image_stats["blobs_already_present"]:,}'
          f', patched={image_stats["patched_missing_image"]:,}'
          f', blob failed={image_stats["failed_to_check_blob"]:,}'
          f', archive failed={image_stats["failed_to_download_archive"]:,})')


def remove_ne_travel_data_faulty_and_missing_entries(gcp_project, model_name, json_key_path, date_to_process):
    bigquery_client = bigquery.Client.from_service_account_json(json_key_path)
    query = f"""
        DELETE FROM `{gcp_project}.detected_objects.{model_name}`
        WHERE date = "{date_to_process:%Y-%m-%d}"
        AND (faulty OR missing)
        AND source = "NETravelData-images"
        """
    query_job = bigquery_client.query(query)
    _query_result_rows = query_job.result()
