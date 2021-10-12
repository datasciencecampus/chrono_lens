import argparse
import datetime
import json
import logging
import sys
from datetime import date, datetime, timedelta
from os import path, environ

from chrono_lens.exceptions import ProcessImagesException
from chrono_lens.gcloud import process_images

PROJECT_ID = environ.get('PROJECT_ID', None)

available_models = [
    'NewcastleV0',
    'NewcastleV0_StaticObjectFilterV0',
    'FaultyImageFilterV0_NewcastleV0_StaticObjectFilterV0',
]


def get_args(command_line_arguments):
    parser = argparse.ArgumentParser(description="Call Google Cloud Functions to process selected camera images, "
                                                 "in provided data range.",
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    parser.add_argument("-jpk", "--JSON-private-key", required=True, dest='json_key_path', type=str,
                        help='Private key in JSON format used to access Google Cloud Project with OAuth2')

    parser.add_argument("-sd", "--start-date", default=None, type=str, dest='start_date_raw',
                        help='Start date, in the form YYYYMMDD, of when camera images are to be processed;'
                             ' assumed to be yesterday if undefined')

    parser.add_argument("-ed", "--end-date", default=None, type=str, dest='end_date_raw',
                        help='End date, in the form YYYYMMDD, of when camera images are to be processed;'
                             ' assumed to be yesterday if undefined')

    parser.add_argument("-cj", "--cameras-json", required=True,
                        help='File containing list of camera IDs to analyse, in JSON format'
                             ' (key: provider, value=list of camera IDs)')

    parser.add_argument("-mn", "--model-name", required=True, choices=available_models,
                        help=f"Model to use to process imagery")

    parser.add_argument("-gr", "--gcp-region", default="europe-west2", choices=["europe-west2"],
                        help="Google Cloud Platform region where the process_day cloud function is hosted")

    parser.add_argument("-gp", "--gcp-project", default=PROJECT_ID,
                        help="Google Cloud Platform project that hosts the process_day cloud functions")

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

    try:
        with open(args.cameras_json) as json_file:
            args.cameras_to_analyse = json.load(json_file)
    except Exception as e:
        raise ProcessImagesException(f'Failed to read camera IDs from JSON file "{args.cameras_json}"') from e

    return args


def main(command_line_args):
    args = get_args(command_line_args)

    log_output_filename = 'logs/' \
                          + path.splitext(path.basename(args.cameras_json))[0] \
                          + f'_{args.start_date:%Y%m%d}' \
                          + f'_{args.end_date:%Y%m%d}' \
                          + '_' + args.model_name + '.log'

    print()
    print(f'Appending log output to "{log_output_filename}"')
    print()
    logging.basicConfig(filename=log_output_filename, filemode='a', level=logging.DEBUG,
                        format='%(asctime)s %(levelname)s %(message)s',
                        datefmt='%Y-%m-%d %H:%M:%S')

    results, errors = process_images.run_model_on_images(
        start_date=args.start_date,
        end_date=args.end_date,
        json_key_path=args.json_key_path,
        model_blob_name=args.model_name,
        cameras_to_analyse=args.cameras_to_analyse,
        gcp_region=args.gcp_region,
        gcp_project=args.gcp_project
    )

    print()
    print('Results:')
    print()
    for key in results:
        if key == 'Errors':
            for error in results['Errors']:
                print(f'Error "{error}": {results["Errors"][error]}')
        else:
            print(f'{key}: {results[key]}')

    print()
    print('Errors:')
    print()
    if len(errors) == 0:
        print('No errors reported')
    else:
        for error in errors:
            print(f'"{error}"')

    print()


if __name__ == '__main__':
    try:
        main(sys.argv[1:])

    except ProcessImagesException as err:
        print(f"Image processing error: {err.message}")
