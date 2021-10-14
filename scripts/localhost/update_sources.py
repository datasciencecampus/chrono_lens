import argparse
import logging
import sys

import chrono_lens.images.sources.tfl
import chrono_lens.localhost
from chrono_lens.exceptions import ProcessImagesException
from chrono_lens.localhost.sources import update_ingest_sources


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

    update_ingest_sources(args.config_folder)


if __name__ == '__main__':
    try:
        main(sys.argv[1:])

    except ProcessImagesException as err:
        print(f"Image processing error: {err.message}")
