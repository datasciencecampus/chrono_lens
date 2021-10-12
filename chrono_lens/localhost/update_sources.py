import argparse
import json
import logging
import os
import sys

import chrono_lens.images.sources.tfl
import chrono_lens.localhost
from chrono_lens.exceptions import ProcessImagesException


def process_scheduled(config_path):
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


def get_args(command_line_arguments):
    parser = argparse.ArgumentParser(description="Update list of available cameras to download",
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    parser.add_argument("-cf", "--config-folder", default=chrono_lens.localhost.CONFIG_FOLDER,
                        help="Folder where configuration data will be stored")

    parser.add_argument("-ll", "--log-level",
                        default=chrono_lens.localhost.DEFAULT_LOG_LEVEL,
                        choices=['CRITICAL', 'ERROR', 'WARNING', 'INFO', 'DEBUG'],
                        help="Level of detail to report in logs")

    args = parser.parse_args(command_line_arguments)

    return args


def main(command_line_args):
    args = get_args(command_line_args)

    handler = logging.StreamHandler(sys.stdout)
    logging.basicConfig(handlers=[handler], level=logging.getLevelName(args.log_level))

    process_scheduled(args.config_folder)


if __name__ == '__main__':
    try:
        main(sys.argv[1:])

    except ProcessImagesException as err:
        print(f"Image processing error: {err.message}")
