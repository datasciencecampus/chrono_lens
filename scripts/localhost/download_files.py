import argparse
import logging
import sys

import chrono_lens.localhost
from chrono_lens.exceptions import ProcessImagesException
from chrono_lens.localhost.image_downloads import download_all_images


def get_args(command_line_arguments):
    parser = argparse.ArgumentParser(description="Download available cameras to disc",
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    parser.add_argument("-cf", "--config-folder", default=chrono_lens.localhost.CONFIG_FOLDER,
                        help="Folder where configuration data is stored")

    parser.add_argument("-df", "--download-folder", default=chrono_lens.localhost.DOWNLOAD_FOLDER,
                        help="Folder where image data downloaded")

    parser.add_argument("-mda", "--maximum-download-attempts",
                        default=chrono_lens.localhost.MAXIMUM_NUMBER_OF_DOWNLOAD_ATTEMPTS,
                        type=int,
                        help="Maximum number of download attempts per image")

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

    download_all_images(args.config_folder, args.download_folder, args.maximum_download_attempts)


if __name__ == '__main__':
    try:
        main(sys.argv[1:])

    except ProcessImagesException as err:
        print(f"Image processing error: {err.message}")
