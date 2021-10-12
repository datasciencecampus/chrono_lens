import argparse
import json
import sys
from datetime import date, timedelta, datetime
from os import environ

from dateutil import rrule

from chrono_lens.exceptions import ProcessImagesException
from chrono_lens.gcloud.ingest_bulk_netraveldata import upload_camera_images, \
    remove_ne_travel_data_faulty_and_missing_entries

PROJECT_ID = environ.get('PROJECT_ID', None)

available_models = [
    'NewcastleV0',
    'NewcastleV0_StaticObjectFilterV0',
    'FaultyImageFilterV0_NewcastleV0_StaticObjectFilterV0',
]


def get_args(command_line_arguments):
    parser = argparse.ArgumentParser(description="Backfill missing NE Travel Data images, and remove related SQL"
                                                 " entries from BigQuery ready for reprocessing.",
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    parser.add_argument("-jpk", "--JSON-private-key", required=True, dest='json_key_path', type=str,
                        help='Private key in JSON format used to access Google Cloud Project with OAuth2')

    parser.add_argument("-netsj", "--ne-travel-sources-json", required=True,
                        help="File containing list of NE Travel Info source cameras to download from Newcastle"
                             " University's server, in JSON format list of dictionaries, format specific to"
                             " Newcastle's server")

    parser.add_argument("-mn", "--model-name", required=True, choices=available_models,
                        help=f"Model to use to process imagery")

    parser.add_argument("-sd", "--start-date", default=None, type=str, dest='start_date_raw',
                        help='Start date, in the form YYYYMMDD, of when camera images are to be processed;'
                             ' assumed to be yesterday if undefined')

    parser.add_argument("-ed", "--end-date", default=None, type=str, dest='end_date_raw',
                        help='End date, in the form YYYYMMDD, of when camera images are to be processed;'
                             ' assumed to be yesterday if undefined')

    parser.add_argument("-gr", "--gcp-region", default="europe-west2", choices=["europe-west2"],
                        help="Google Cloud Platform region where the process_day cloud function is hosted")

    parser.add_argument("-gp", "--gcp-project", default=PROJECT_ID,
                        help="Google Cloud Platform project that hosts the process_day cloud functions")

    args = parser.parse_args(command_line_arguments)

    try:
        with open(args.ne_travel_sources_json) as json_file:
            args.ne_travel_sources = json.load(json_file)
    except Exception as e:
        raise ProcessImagesException('Failed to read NE Travel Sources from JSON file '
                                     f'"{args.ne_travel_sources_json}"') from e

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

    print(f"Accessing '{args.gcp_project}' in region '{args.gcp_region}'")
    print(
        f"Pulling missing NE Travel Data images from {args.start_date:%Y-%m-%d} to {args.end_date:%Y-%m-%d} inclusive")

    dates_to_process = list(rrule.rrule(rrule.DAILY, dtstart=args.start_date, until=args.end_date))
    for date_to_process in dates_to_process:
        print(f'Uploading images from {date_to_process:%Y-%m-%d}...')
        upload_camera_images(
            args.ne_travel_sources,
            date_to_process,
            json_key_path=args.json_key_path,
            gcp_project=args.gcp_project
        )
        print(f'Uploading images from {date_to_process:%Y-%m-%d}... done')

        # flush SQL
        print(f'Removing missing or faulty NE travel info images from {date_to_process:%Y-%m-%d}...')
        remove_ne_travel_data_faulty_and_missing_entries(args.gcp_project, args.model_name, args.json_key_path,
                                                         date_to_process)
        print(f'Removing missing or faulty NE travel info images from {date_to_process:%Y-%m-%d}... done')

        print()
        print(f'Reprocessing NE travel info images from {date_to_process:%Y-%m-%d}... done')


if __name__ == '__main__':
    try:
        main(sys.argv[1:])

    except ProcessImagesException as err:
        print(f"Image processing error: {err.message}")
