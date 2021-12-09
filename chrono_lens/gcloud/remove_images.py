import datetime

from google.api_core import page_iterator
from tqdm import tqdm


def _list_directories(client, bucket_name, prefix):
    """
    From https://stackoverflow.com/questions/37074977/how-to-get-list-of-folders-in-a-given-bucket-using-google-cloud-api
    """

    def _item_to_value(iterator, item):
        return item

    if not prefix.endswith('/'):
        prefix += '/'

    extra_params = {
        "projection": "noAcl",
        "prefix": prefix,
        "delimiter": '/'
    }

    blob_path = "/b/" + bucket_name + "/o"

    iterator = page_iterator.HTTPIterator(
        client=client,
        api_request=client._connection.api_request,
        path=blob_path,
        items_key='prefixes',
        item_to_value=_item_to_value,
        extra_params=extra_params,
    )

    return [x for x in iterator]


def remove_images_older_than_threshold(maximum_number_of_days, data_bucket_name, supplier_names_to_camera_counts,
                                       storage_client):
    print(f"Sifting images in '{data_bucket_name}' bucket")

    today = datetime.date.today()

    number_of_images_deleted = 0
    with tqdm(supplier_names_to_camera_counts, unit='image supplier', leave=False) as suppliers_progress_bar:
        for supplier_name in suppliers_progress_bar:
            suppliers_progress_bar.set_description(f'Sifting {supplier_name}')

            supplier_date_folders = _list_directories(storage_client, data_bucket_name, supplier_name)
            with tqdm(supplier_date_folders, unit='dates', leave=False) as supplier_date_progress_bar:
                for supplier_date_to_empty in supplier_date_progress_bar:
                    supplier_date_progress_bar.set_description(f'Sifting {supplier_date_to_empty}')

                    folder_date_iso_string = supplier_date_to_empty.split('/')[1]
                    try:
                        folder_date = datetime.datetime.strptime(folder_date_iso_string, "%Y%m%d").date()
                    except ValueError:
                        # failed to parse date, so warn and move on
                        print(f'Folder {supplier_date_to_empty} not in date format YYYYMMDD so skipping')
                        continue

                    age_in_days = (today - folder_date).days

                    # if date is older than...
                    if age_in_days > maximum_number_of_days:
                        image_blobs_to_delete = list(storage_client.list_blobs(data_bucket_name,
                                                                               prefix=supplier_date_to_empty))

                        # Maximum 100/batch as per https://cloud.google.com/storage/docs/json_api/v1/how-tos/batch
                        max_images_per_blob = 100
                        image_blobs_batches_to_delete = [image_blobs_to_delete[i:i + max_images_per_blob]
                                                         for i in range(0, len(image_blobs_to_delete),
                                                                        max_images_per_blob)]
                        for image_blobs_batch_to_delete in tqdm(
                                image_blobs_batches_to_delete, desc=f"Deleting batches of {max_images_per_blob} images",
                                unit='batch', leave=False):

                            with storage_client.batch():

                                for image_blob_to_delete in image_blobs_batch_to_delete:
                                    number_of_images_deleted += 1
                                    image_blob_to_delete.delete()

    print(f'...sifting images in bucket {data_bucket_name} complete; deleted {number_of_images_deleted} images')
