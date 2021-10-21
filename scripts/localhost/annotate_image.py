import argparse
import logging
import sys

import chrono_lens.images.sources.tfl
import chrono_lens.localhost
from chrono_lens.exceptions import ProcessImagesException
from chrono_lens.localhost.process_images import markup_image_with_detected_objects


def get_args(command_line_arguments):
    parser = argparse.ArgumentParser(description="Run detection model over selected image "
                                                 "and highlight detected objects",
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    parser.add_argument("-cf", "--config-folder", default=chrono_lens.localhost.CONFIG_FOLDER,
                        help="Folder where configuration data will be stored")

    parser.add_argument("-m", "--model",
                        default="NewcastleV0",
                        choices=['NewcastleV0'],
                        help="Model to process image with")

    parser.add_argument("-ll", "--log-level",
                        default=chrono_lens.localhost.DEFAULT_LOG_LEVEL,
                        choices=['CRITICAL', 'ERROR', 'WARNING', 'INFO', 'DEBUG'],
                        help="Level of detail to report in logs")

    parser.add_argument("-of", "--output-folder", default=".",
                        help="Where to store augmented image")

    parser.add_argument("image_filename", metavar='image filename',
                        help="Name of image file to import and mark up")

    args = parser.parse_args(command_line_arguments)

    return args


def main(command_line_args):
    args = get_args(command_line_args)

    handler = logging.StreamHandler(sys.stdout)
    logging.basicConfig(handlers=[handler], level=logging.getLevelName(args.log_level))

    markup_image_with_detected_objects(args.image_filename, args.model, args.config_folder, args.output_folder)


if __name__ == '__main__':
    try:
        main(sys.argv[1:])

    except ProcessImagesException as err:
        print(f"Image processing error: {err.message}")
