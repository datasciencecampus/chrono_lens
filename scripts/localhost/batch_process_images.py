import argparse
import logging
import sys
from datetime import date, datetime, timedelta

import chrono_lens.localhost
from chrono_lens.exceptions import ProcessImagesException
from chrono_lens.localhost.process_images import batch_process


# todo: add this support back in - but instead scan the config folder for available models (given its local disc)
# available_models = [
#     'NewcastleV0',
#     'NewcastleV0_StaticObjectFilterV0',
#     'FaultyImageFilterV0_NewcastleV0_StaticObjectFilterV0',
# ]


def get_args(command_line_arguments):
    parser = argparse.ArgumentParser(description="Process configured camera images on provided data range.",
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    parser.add_argument("-sd", "--start-date", default=None, type=str, dest='start_date_raw',
                        help='Start date, in the form YYYYMMDD, of when camera images are to be processed;'
                             ' assumed to be yesterday if undefined')

    parser.add_argument("-ed", "--end-date", default=None, type=str, dest='end_date_raw',
                        help='End date, in the form YYYYMMDD, of when camera images are to be processed;'
                             ' assumed to be yesterday if undefined')

    # parser.add_argument("-mn", "--model-name", required=True, choices=available_models,
    #                     help=f"Model to use to process imagery")

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

    if args.start_date_raw is None:
        args.start_date = date.today() - timedelta(days=1)
    else:
        if len(args.start_date_raw) != 8:
            raise ProcessImagesException('Start date not in format "YYYYMMDD" or invalid date')

        try:
            args.start_date = datetime.strptime(args.start_date_raw, "%Y%m%d").date()
        except Exception as e:
            raise ProcessImagesException('Start date not in format "YYYYMMDD" or invalid date') from e

    if args.end_date_raw is None:
        args.end_date = date.today() - timedelta(days=1)
    else:
        if len(args.end_date_raw) != 8:
            raise ProcessImagesException('End date not in format "YYYYMMDD" or invalid date')

        try:
            args.end_date = datetime.strptime(args.end_date_raw, "%Y%m%d").date()
        except Exception as e:
            raise ProcessImagesException('End date not in format "YYYYMMDD" or invalid date') from e

    if args.start_date > args.end_date:
        raise ProcessImagesException("Start date after end date")

    return args


def main(command_line_args):
    args = get_args(command_line_args)

    handler = logging.StreamHandler(sys.stdout)
    logging.basicConfig(handlers=[handler], level=logging.getLevelName(args.log_level))

    batch_process(
        config_path=args.config_folder,
        download_path=args.download_folder,
        counts_path=args.counts_path,
        start_date=args.start_date,
        end_date=args.end_date
    )


if __name__ == '__main__':
    try:
        main(sys.argv[1:])

    except ProcessImagesException as err:
        print(f"Image processing error: {err.message}")
