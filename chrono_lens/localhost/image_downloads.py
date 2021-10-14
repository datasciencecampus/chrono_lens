import glob
import json
import logging
import os
from datetime import datetime, timedelta
from random import uniform
from time import sleep
from urllib.parse import urlparse

import requests
from tqdm import tqdm

import chrono_lens.localhost
from chrono_lens.images.correction import resize_jpeg_image, IMAGE_MAX_AXIS_THRESHOLD


def download_image_to_disc(image_url, target_file_name, maximum_number_of_download_attempts):
    response = None
    for attempt_number in range(maximum_number_of_download_attempts):
        try:
            response = requests.get(image_url)

            if response.status_code == 200 or response.status_code == 404:
                break

            logging.debug(
                f'Failed attempt#{attempt_number}: code={response.status_code} with URL="{image_url}";')

        except ConnectionError as re:
            logging.debug(f'Failed attempt#{attempt_number}: requests.get errored with "{re}"')

        # No need to wait after the last attempt, we've given up now - so don't waste compute cycles
        if attempt_number < maximum_number_of_download_attempts - 1:
            sleep(chrono_lens.localhost.DOWNLOAD_RETRY_SLEEP_MINIMUM
                  + uniform(1,
                            chrono_lens.localhost.DOWNLOAD_RETRY_SLEEP_MAXIMUM
                            - chrono_lens.localhost.DOWNLOAD_RETRY_SLEEP_MINIMUM))

    if response.status_code == 404:
        logging.warning(f'Failed to access URL="{image_url}" with error code #404 (file not found)')
        return

    elif response.status_code != 200:
        logging.error(f'Failed to access URL="{image_url}" with error code #{response.status_code}')
        return

    resized_jpeg_image = resize_jpeg_image(response.content, IMAGE_MAX_AXIS_THRESHOLD)

    if resized_jpeg_image is None:
        logging.error(f'Failed to decode URL="{image_url}"  - empty bitmap generated')

    else:
        with open(target_file_name, 'wb') as binary_image_file:
            binary_image_file.write(resized_jpeg_image)


def download_all_images(config_folder_name, download_folder_name, maximum_number_of_download_attempts):
    now = datetime.now()
    now = now - timedelta(minutes=now.minute % 10, seconds=now.second, microseconds=now.microsecond)
    date_time_folder = os.path.join(f'{now:%Y%m%d}', f'{now:%H%M}')

    sources_folder_name = os.path.join(config_folder_name, 'ingest')

    logging.info(f'Searching folder {sources_folder_name} for JSON files...')

    images_tuples_to_download = []
    number_of_urls_read = 0
    number_of_files_read = 0
    for json_filename in glob.glob(os.path.join(sources_folder_name, '*.json')):
        logging.debug(f'=>  Reading URLs from {json_filename}')
        base_json_name = os.path.basename(json_filename)
        base_name = os.path.splitext(base_json_name)[0]

        with open(json_filename, 'r') as json_file:
            image_urls = json.load(json_file)
            number_of_urls_read += len(image_urls)
            number_of_files_read += 1

        for image_url in image_urls:
            images_tuples_to_download.append((base_name, image_url))

    logging.info(f'...search in folder {sources_folder_name} for JSON files complete;'
                 f' read in {number_of_urls_read} image URLs across {number_of_files_read} files.')

    destination_folder_message = os.path.join(download_folder_name, "IMAGE_PROVIDER", date_time_folder, "...")
    logging.info(f'Downloading images to {destination_folder_message}')
    for image_tuple_to_download in tqdm(images_tuples_to_download, desc='Downloading images', unit='images'):
        base_name = image_tuple_to_download[0]
        image_url = image_tuple_to_download[1]

        parsed_file_url = urlparse(image_url)
        base_file_name = os.path.basename(parsed_file_url.path[1:])
        target_folder_name = os.path.join(download_folder_name, base_name, date_time_folder)
        os.makedirs(target_folder_name, exist_ok=True)
        target_file_name = os.path.join(target_folder_name, base_file_name)

        logging.debug(f'Downloading {image_url} to {target_file_name}')
        download_image_to_disc(image_url, target_file_name, maximum_number_of_download_attempts)

    logging.info(f'...downloaded {len(images_tuples_to_download)} images to {destination_folder_message}')
