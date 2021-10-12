import json

from google.cloud import storage


def write_to_bucket(bucket_name, blob_name, data, content_type='text/plain'):
    client = storage.Client()

    bucket = client.get_bucket(bucket_name)
    blob = bucket.blob(blob_name)

    blob.upload_from_string(data, content_type=content_type)


def read_from_bucket(bucket_name, blob_name, client=None):
    if client is None:
        client = storage.Client()

    bucket = client.get_bucket(bucket_name)
    blob = bucket.blob(blob_name)

    data = blob.download_as_string()

    return data


def fetch_blob_as_json(bucket_name, blob_name, json_credentials_filename=None):
    if json_credentials_filename is None:
        client = storage.Client()
    else:
        client = storage.Client.from_service_account_json(json_credentials_filename)

    bucket = client.get_bucket(bucket_name)
    blob = bucket.blob(blob_name)

    data = blob.download_as_string()

    return json.loads(data)
