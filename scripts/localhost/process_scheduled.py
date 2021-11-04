import argparse
import logging
import sys

import chrono_lens.images.sources.tfl
import chrono_lens.localhost
from chrono_lens.exceptions import ProcessImagesException
from chrono_lens.localhost.process_images import process_scheduled


def get_args(command_line_arguments):
    parser = argparse.ArgumentParser(description="Runs configured model over stored images to generate object counts",
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    parser.add_argument("-cf", "--config-folder", default=chrono_lens.localhost.CONFIG_FOLDER,
                        help="Folder where configuration data is stored")

    parser.add_argument("-df", "--download-folder", default=chrono_lens.localhost.DOWNLOAD_FOLDER,
                        help="Folder where image data downloaded")

    parser.add_argument("-cp", "--counts-path", default=chrono_lens.localhost.COUNTS_FOLDER,
                        help="Folder where image counts are stored")

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

    process_scheduled(args.config_folder, args.download_folder, args.counts_path)


if __name__ == '__main__':
    try:
        main(sys.argv[1:])

    except ProcessImagesException as err:
        print(f"Image processing error: {err.message}")
