import datetime
import json
import os
from unittest import TestCase, mock
from unittest.mock import MagicMock

import google.cloud.storage

function_region = 'region'
gcp_project = 'project'
with mock.patch('chrono_lens.gcloud.logging.setup_logging_and_trace'):
    with mock.patch.dict(os.environ, {'FUNCTION_REGION': function_region, 'GCP_PROJECT': gcp_project}):
        import main


def create_mock_request(request_json):
    mock_request = MagicMock()
    mock_request.get_json = MagicMock(return_value=request_json)
    return mock_request


def create_mock_bucket(bucket_blob_data_maps):
    blob_name_to_blob = {}

    for blob_name, blob_data in bucket_blob_data_maps:
        mock_blob = MagicMock()
        if blob_data is None:
            mock_blob.download_as_string.side_effect = google.api_core.exceptions.NotFound('whoops')
        else:
            mock_blob.download_as_string.return_value = blob_data

        blob_name_to_blob[blob_name] = mock_blob

    mock_bucket = MagicMock()
    mock_bucket.blob.side_effect = blob_name_to_blob.get

    return mock_bucket


class TestMain(TestCase):

    @mock.patch('main.run_cloud_function_async_with_parameter_list')
    @mock.patch('google.cloud.storage.Client')
    @mock.patch('main.datetime')
    @mock.patch('main.logging')
    def test_reported_errors_logged(self, mock_logging, mock_datetime, mock_client, mock_run_async):
        datetime_now = datetime.datetime(year=1999, month=1, day=1, hour=2, minute=3, second=4, microsecond=5)
        mock_datetime.now.return_value = datetime_now

        mock_client_instance = MagicMock()

        mock_blob = MagicMock()
        data_root = 'Supplier'
        mock_blob.name = f'ingest/{data_root}.json'
        camera_id = 'camera1'
        mock_blob.download_as_string.return_value = f'["{camera_id}"]'
        mock_client_instance.list_blobs.return_value = [mock_blob, mock_blob, mock_blob, mock_blob, mock_blob,
                                                        mock_blob]

        mock_client.return_value = mock_client_instance

        mock_run_async.return_value = [
            {"STATUS": "OK", 'Counts': {'OK': 1, 'Errored': 2}},
            {"STATUS": "uh oh how weird"},
            {
                'STATUS': 'Errored',
                'Message': 'Forbidden - not authorised with "..."',
                'TextResponse': '',
                'JsonResponse': ''
            },
            {"STATUS": "OK", 'Counts': {'OK': 7}},
            {
                'STATUS': 'Errored',
                'Message': 'Failed after 7 attempts with "dummy"',
                'TextResponse': '',
                'JsonResponse': ''
            },
            {"STATUS": "OK", 'Counts': {'Errored': 3}},
        ]

        mock_event = MagicMock()
        mock_context = MagicMock()

        with mock.patch.dict(os.environ, {'SOURCES_BUCKET_NAME': 'rhubarb'}):
            response_json = main.distribute_json_sources(mock_event, mock_context)

        response = json.loads(response_json)

        self.assertEqual('OK', response['STATUS'])
        self.assertEqual({"OK": 8, "Errored": 5}, response['Counts'])

        mock_logging.critical.assert_any_call('Incomplete execution - possible outage; "ingest/Supplier.json" results:'
                                              ' {\'STATUS\': \'Errored\','
                                              ' \'Message\': \'Forbidden - not authorised with "..."\','
                                              ' \'TextResponse\': \'\','
                                              ' \'JsonResponse\': \'\'}')
        mock_logging.critical.assert_any_call('Incomplete execution - possible outage; "ingest/Supplier.json" results:'
                                              ' {\'STATUS\': \'Errored\','
                                              ' \'Message\': \'Failed after 7 attempts with "dummy"\','
                                              ' \'TextResponse\': \'\','
                                              ' \'JsonResponse\': \'\'}')
        mock_logging.error.assert_any_call("Unexpected STATUS type; result: {'STATUS': 'uh oh how weird'}")

    @mock.patch('main.run_cloud_function_async_with_parameter_list')
    @mock.patch('google.cloud.storage.Client')
    @mock.patch('main.datetime')
    @mock.patch('main.logging')
    def test_check_time_rounded_down_to_nearest_10_minutes(self, _mock_logging, mock_datetime, mock_client,
                                                           mock_run_async):
        datetime_now = datetime.datetime(year=1999, month=1, day=1, hour=2, minute=3, second=4, microsecond=5)
        mock_datetime.now.return_value = datetime_now

        mock_client_instance = MagicMock()

        mock_blob = MagicMock()
        data_root = 'Supplier'
        mock_blob.name = f'ingest/{data_root}.json'
        camera_id = 'camera1'
        mock_blob.download_as_string.return_value = f'["{camera_id}"]'
        mock_client_instance.list_blobs.return_value = [mock_blob]

        mock_client.return_value = mock_client_instance

        mock_run_async.return_value = [
            {"STATUS": "OK", 'Counts': {'OK': 3}},
        ]

        mock_event = MagicMock()
        mock_context = MagicMock()

        with mock.patch.dict(os.environ, {'SOURCES_BUCKET_NAME': 'rhubarb'}):
            response_json = main.distribute_json_sources(mock_event, mock_context)

        _response = json.loads(response_json)

        mock_run_async.assert_called_once_with(
            'json_blob_name', [mock_blob.name],
            {'date_time_folder': f'{datetime_now:%Y%m%d}/0200'},
            f'https://{function_region}-{gcp_project}.cloudfunctions.net/distribute_uri_sources',
            sleep_base=0,
            sleep_tuple=(0, 6)
        )

    @mock.patch('main.run_cloud_function_async_with_parameter_list')
    @mock.patch('google.cloud.storage.Client')
    @mock.patch('main.datetime')
    @mock.patch('main.logging')
    def test_check_time_rounded_down_to_nearest_10_minutes_already_rounded(self, _mock_logging, mock_datetime,
                                                                           mock_client, mock_run_async):
        datetime_now = datetime.datetime(year=1999, month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        mock_datetime.now.return_value = datetime_now

        mock_client_instance = MagicMock()

        mock_blob = MagicMock()
        data_root = 'Supplier'
        mock_blob.name = f'ingest/{data_root}.json'
        camera_id = 'camera1'
        mock_blob.download_as_string.return_value = f'["{camera_id}"]'
        mock_client_instance.list_blobs.return_value = [mock_blob]

        mock_client.return_value = mock_client_instance

        mock_run_async.return_value = [
            {"STATUS": "OK", 'Counts': {'OK': 3}},
        ]

        mock_event = MagicMock()
        mock_context = MagicMock()

        with mock.patch.dict(os.environ, {'SOURCES_BUCKET_NAME': 'rhubarb'}):
            response_json = main.distribute_json_sources(mock_event, mock_context)

        _response = json.loads(response_json)

        mock_run_async.assert_called_once_with(
            'json_blob_name', [mock_blob.name],
            {'date_time_folder': f'{datetime_now:%Y%m%d}/0000'},
            f'https://{function_region}-{gcp_project}.cloudfunctions.net/distribute_uri_sources',
            sleep_base=0,
            sleep_tuple=(0, 6)
        )
