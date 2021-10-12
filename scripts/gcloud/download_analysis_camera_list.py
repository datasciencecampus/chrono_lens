import argparse
import sys
from json import loads, dump
from os import environ, path

from google.cloud import storage

PROJECT_ID = environ.get('PROJECT_ID', None)


def get_args(command_line_arguments):
    parser = argparse.ArgumentParser(description="Pull 'analyse' JSON files from sources bucket "
                                                 "and collect in single JSON",
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    parser.add_argument("-ctaf", "--cameras-to-analyse-file", required=True, type=str,
                        help='Output JSON file where cameras to be analysed will be stored')

    parser.add_argument("-mcf", "--model-config-file", required=True, type=str,
                        help='Output model name file where model name in use by scheduled analysis will be stored')

    parser.add_argument("-jpk", "--JSON-private-key", required=True, dest='json_key_path', type=str,
                        help='Private key in JSON format used to access Google Cloud Project with OAuth2')

    parser.add_argument("-gp", "--gcp-project", default=PROJECT_ID,
                        help="Google Cloud Platform project that hosts the sources bucket")

    args = parser.parse_args(command_line_arguments)

    return args


def main(command_line_args):
    args = get_args(command_line_args)

    print(f"Accessing '{args.gcp_project}'")
    print(f"Pulling lists of cameras to analyse in 'sources' bucket")

    sources_bucket_name = f'sources-{args.gcp_project}'
    blob_prefix = 'analyse'
    print(f'Searching bucket "{sources_bucket_name}/{blob_prefix}"" for JSON files...')

    storage_client = storage.Client.from_service_account_json(args.json_key_path)

    blobs = storage_client.list_blobs(sources_bucket_name, prefix=blob_prefix + '/')

    camera_sources = {}
    for blob in blobs:
        if blob.name.endswith(".json"):
            print(f'=>  Reading URLs from {blob.name}')
            json_data = blob.download_as_string()
            camera_ids = loads(json_data)

            data_json_name = path.basename(blob.name)
            data_root = path.splitext(data_json_name)[0]

            camera_sources[data_root] = camera_ids

    print(f'...search in bucket {sources_bucket_name}/{blob_prefix} for JSON files complete.')

    print(f'Output camera lists to "{args.cameras_to_analyse_file}" ...')
    with open(args.cameras_to_analyse_file, 'w') as camera_file:
        dump(camera_sources, camera_file, indent=4, sort_keys=True)
    print(f'Output camera lists to "{args.cameras_to_analyse_file}" ... complete.')

    analysis_configuration_name = "analyse-configuration.json"
    print(f'Reading configuration "{analysis_configuration_name}" from "{sources_bucket_name}" bucket...')
    sources_bucket = storage_client.bucket(sources_bucket_name)
    sources_blob = sources_bucket.blob(analysis_configuration_name)
    model_json_data = sources_blob.download_as_string()
    model_json = loads(model_json_data)

    with open(args.model_config_file, 'w') as model_config_file:
        print(f'{model_json["model_blob_name"]}', end='', file=model_config_file)

    print(f'Model configuration written to "{args.model_config_file}"')


if __name__ == '__main__':
    main(sys.argv[1:])
