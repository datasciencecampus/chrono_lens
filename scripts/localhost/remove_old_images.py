import argparse
import logging
import sys

import chrono_lens
from chrono_lens.localhost.remove_images import remove_images_older_than_threshold


def get_args(command_line_arguments):
    parser = argparse.ArgumentParser(description="Remove images from the data bucket that are older than the specified"
                                                 "threshold",
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    parser.add_argument("-mnod", "--maximum-number-of-days", type=int,
                        default=chrono_lens.localhost.DEFAULT_IMAGES_MAXIMUM_DAYS_TO_RETAIN,
                        help='Maximum number of days old an image is allowed to be before it is deleted')

    parser.add_argument("-df", "--download-folder", default=chrono_lens.localhost.DOWNLOAD_FOLDER,
                        help="Folder where image data downloaded")

    parser.add_argument("-ll", "--log-level",
                        default=chrono_lens.localhost.DEFAULT_LOG_LEVEL,
                        choices=['CRITICAL', 'ERROR', 'WARNING', 'INFO', 'DEBUG'],
                        help="Level of detail to report in logs")

    args = parser.parse_args(command_line_arguments)

    if args.maximum_number_of_days < 1:
        raise ValueError("--maximum-number-of-days must be 1 or higher")

    return args


def main(command_line_args):
    args = get_args(command_line_args)

    handler = logging.StreamHandler(sys.stdout)
    logging.basicConfig(handlers=[handler], level=logging.getLevelName(args.log_level))

    remove_images_older_than_threshold(args.maximum_number_of_days, args.download_folder)


if __name__ == '__main__':
    main(sys.argv[1:])
