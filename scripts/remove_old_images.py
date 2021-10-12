import argparse
import json
import sys
from os import environ, path

from google.cloud import storage

from chrono_lens.gcloud.remove_images import remove_images_older_than_threshold

PROJECT_ID = environ.get('PROJECT_ID', None)


def get_args(command_line_arguments):
    parser = argparse.ArgumentParser(description="Remove images from the data bucket that are older than the specified"
                                                 "threshold",
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    parser.add_argument("-mnod", "--maximum-number-of-days", required=True, type=int,
                        help='Maximum number of days old an image is allowed to be before it is deleted')

    parser.add_argument("-jpk", "--JSON-private-key", required=True, dest='json_key_path', type=str,
                        help='Private key in JSON format used to access Google Cloud Project with OAuth2')

    parser.add_argument("-gr", "--gcp-region", default="europe-west2", choices=["europe-west2"],
                        help="Google Cloud Platform region where the data bucket is hosted")

    parser.add_argument("-gp", "--gcp-project", default=PROJECT_ID,
                        help="Google Cloud Platform project that hosts the data bucket")

    args = parser.parse_args(command_line_arguments)

    if args.maximum_number_of_days < 1:
        raise ValueError("--maximum-number-of-days must be 1 or higher")

    return args


def main(command_line_args):
    args = get_args(command_line_args)

    print(f"Accessing '{args.gcp_project}' in region '{args.gcp_region}'")
    data_bucket_name = f'data-{args.gcp_project}'

    storage_client = storage.Client.from_service_account_json(args.json_key_path)

    # work-around; can't get list of root folders in a bucket, so using alternative source...
    sources_bucket_name = f'sources-{args.gcp_project}'
    blob_prefix = 'ingest'

    print(f'Searching bucket "{sources_bucket_name}/{blob_prefix}"" for JSON files...')
    supplier_names_to_camera_counts = {}
    blobs = storage_client.list_blobs(sources_bucket_name, prefix=blob_prefix + '/')
    for blob in blobs:
        supplier_name = path.splitext(path.basename(blob.name))[0]
        json_data = blob.download_as_string()
        camera_ids = json.loads(json_data)
        supplier_names_to_camera_counts[supplier_name] = len(camera_ids)
    print(f'...searching bucket "{sources_bucket_name}/{blob_prefix}"" for JSON files complete')

    # Manually add NETravelData-images as this isn't pulled via JSON (Cloud Function distribute_ne_travel_data used)
    supplier_names_to_camera_counts['NETravelData-images'] = 350

    remove_images_older_than_threshold(args.maximum_number_of_days, data_bucket_name, supplier_names_to_camera_counts,
                                       storage_client)


if __name__ == '__main__':
    main(sys.argv[1:])
