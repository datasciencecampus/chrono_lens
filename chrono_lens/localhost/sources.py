import json
import logging
import os

import chrono_lens.images.sources.tfl
import chrono_lens.localhost


def update_ingest_sources(config_path):
    logging.info(f'Updating TfL image sources...')
    config_path = os.path.join(config_path, 'ingest')
    os.makedirs(config_path, exist_ok=True)

    # Search folder for .json
    # Each filename = data source, a folder name to read images from
    # viz folder.json => config/data/FOLDER/YEAR-MONTH/DAY/HOURS--MINUTES/CAMERANAME.jpg

    tfl_images_destination = os.path.join(config_path, 'TfL-images.json')
    tfl_sources = chrono_lens.images.sources.tfl.download_urls()
    url_list = chrono_lens.images.sources.tfl.filter_image_urls(tfl_sources)
    with open(tfl_images_destination, 'w') as f:
        json.dump(url_list, f)
    logging.info(f'...TfL image sources updated.')
