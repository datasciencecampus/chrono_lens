import datetime
import logging

import google.auth.transport.requests
import google.oauth2.service_account
from dateutil import rrule
from tqdm import tqdm

from dsc_lib.gcloud.async_functions import run_cloud_function_async_with_parameter_list

CAMERA_BATCH_SIZE = 50


def run_model_on_images(start_date: datetime.date, end_date: datetime.date, cameras_to_analyse: dict,
                        model_blob_name: str, json_key_path: str, gcp_region: str, gcp_project: str):
    process_day_endpoint = f'https://{gcp_region}-{gcp_project}.cloudfunctions.net/process_day'

    logging.info(f'Using endpoint "{process_day_endpoint}"')

    credentials = google.oauth2.service_account.IDTokenCredentials.from_service_account_file(
        json_key_path, target_audience=process_day_endpoint)
    google_authentication_request = google.auth.transport.requests.Request()

    dates_to_process = list(rrule.rrule(rrule.DAILY, dtstart=start_date, until=end_date))
    results = {'Errors': {}}
    errors = []
    for date_to_process in tqdm(dates_to_process, desc='Processing dates', unit='day', leave=False):
        credentials.refresh(google_authentication_request)

        for data_root in tqdm(cameras_to_analyse, desc='Processing image sources', unit='image source', leave=False):

            camera_batches = [cameras_to_analyse[data_root][x:x + CAMERA_BATCH_SIZE]
                              for x in range(0, len(cameras_to_analyse[data_root]), CAMERA_BATCH_SIZE)]
            for camera_batch in camera_batches:
                async_results = run_cloud_function_async_with_parameter_list(
                    json_key='camera_id', json_values=camera_batch,
                    partial_json={
                        'date_to_process': f'{date_to_process:%Y%m%d}',
                        'data_root': data_root,
                        'model_blob_name': model_blob_name
                    },
                    endpoint=process_day_endpoint,
                    headers={'Authorization': f'Bearer {credentials.token}'}
                )

                for result in async_results:
                    if result['STATUS'] == 'OK':
                        for count_type in result['Counts']:
                            results[count_type] = results.get(count_type, 0) + result['Counts'][count_type]
                    else:
                        results['Errors'][result['STATUS']] = results['Errors'].get(result['STATUS'], 0) + 1
                        errors.append(result)

    return results, errors
