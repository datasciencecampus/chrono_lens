import json

from google.cloud import storage


def fetch_blob_as_json(bucket_name, blob_name, json_credentials_filename=None):
    if json_credentials_filename is None:
        client = storage.Client()
    else:
        client = storage.Client.from_service_account_json(json_credentials_filename)

    bucket = client.get_bucket(bucket_name)
    blob = bucket.blob(blob_name)

    data = blob.download_as_string()

    return json.loads(data)
