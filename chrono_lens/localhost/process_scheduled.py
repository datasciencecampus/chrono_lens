import argparse
import json
import logging
import os
import sys

import chrono_lens.images.sources.tfl
import chrono_lens.localhost
import chrono_lens.localhost.logging_support
from chrono_lens.exceptions import ProcessImagesException

chrono_lens.localhost.logging_support.setup_logging()


def refresh_all_sources(config_path):
    logging.info(f'Updating TfL image sources...')
    config_path = os.path.join(config_path, 'ingest')
    os.makedirs(config_path, exist_ok=True)

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

    args = parser.parse_args(command_line_arguments)

    return args


def main(command_line_args):
    args = get_args(command_line_args)

    refresh_all_sources(args.config_folder)


if __name__ == '__main__':
    try:
        main(sys.argv[1:])

    except ProcessImagesException as err:
        print(f"Image processing error: {err.message}")
