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
