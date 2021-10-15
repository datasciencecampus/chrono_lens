import datetime
import logging
import os
import shutil
from pathlib import Path

from tqdm import tqdm


def remove_images_older_than_threshold(maximum_number_of_days, download_folder_name):
    today = datetime.date.today()

    logging.info(f'Scanning download folder "{download_folder_name}" '
                 f'for images older than {maximum_number_of_days} days')

    number_of_folders_deleted = 0

    download_path = Path(download_folder_name)
    image_supplier_folders = [folder_entry for folder_entry in download_path.iterdir() if folder_entry.is_dir()]

    for image_supplier_folder in tqdm(image_supplier_folders, desc='Scanning image supplier folders', unit='folders'):
        logging.debug(f'Searching {image_supplier_folder} for images older than {maximum_number_of_days} days...')

        image_supplier_path = Path(image_supplier_folder)
        image_folders = [folder_entry for folder_entry in image_supplier_path.iterdir() if folder_entry.is_dir()]

        for image_folder in tqdm(image_folders, desc=f'Scanning {image_supplier_folder}', unit='folders', leave=False):
            folder_base_name = os.path.basename(image_folder)
            try:
                folder_date = datetime.datetime.strptime(folder_base_name, '%Y%m%d').date()
            except ValueError:
                # Not a date folder
                logging.debug(f'Skipping folder "{image_folder}" as not in date format')
                continue

            folder_age_in_days = (today - folder_date).days

            if folder_age_in_days > maximum_number_of_days:
                logging.debug(f'Removing download folder "{image_folder}"...')
                shutil.rmtree(image_folder)
                number_of_folders_deleted += 1
                logging.debug(f'...removed download folder "{image_folder}".')

    logging.info(f'Deleted {number_of_folders_deleted} folders as dated older than {maximum_number_of_days} days')
