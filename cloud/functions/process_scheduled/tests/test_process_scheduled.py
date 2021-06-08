import datetime
import json
import os
from unittest import TestCase, mock
from unittest.mock import MagicMock

import google.cloud.storage

with mock.patch('dsc_lib.gcloud.logging.setup_logging_and_trace'):
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


class TestProcessScheduled(TestCase):

    @mock.patch('google.cloud.storage.Client')
    def test_undefined_source_bucket_name_returns_error(self, mock_client):
        mock_client_instance = MagicMock()

        mock_event = MagicMock()
        mock_context = MagicMock()

        with mock.patch.dict(os.environ, {}):
            mock_client.return_value = mock_client_instance
            response_json = main.process_scheduled(mock_event, mock_context)

        response = json.loads(response_json)

        self.assertEqual('Errored', response['STATUS'])
        self.assertEqual('RuntimeError: "SOURCES_BUCKET_NAME" not defined as an environment variable',
                         response['Message'])

    @mock.patch('google.cloud.storage.Client')
    @mock.patch('main.datetime')
    def test_fails_to_read_model_config(self, mock_datetime, mock_client):
        mock_datetime.now.return_value = datetime.datetime(year=1999, month=1, day=1, hour=2, minute=3,
                                                           second=4, microsecond=5)

        mock_client_instance = MagicMock()
        mock_client_instance.get_bucket.return_value = create_mock_bucket([
            (f'analyse-configuration.json', None)
        ])

        mock_client.return_value = mock_client_instance
        mock_event = MagicMock()
        mock_context = MagicMock()

        with mock.patch.dict(os.environ, {'SOURCES_BUCKET_NAME': 'rhubarb'}):
            response_json = main.process_scheduled(mock_event, mock_context)

        response = json.loads(response_json)

        self.assertEqual('Errored', response['STATUS'])
        self.assertEqual(f'NotFound: whoops', response['Message'])

    @mock.patch('google.cloud.storage.Client')
    @mock.patch('main.datetime')
    def test_no_data_blobs_listed_returns_empty_counts(self, mock_datetime, mock_client):
        mock_datetime.now.return_value = datetime.datetime(year=1999, month=1, day=1, hour=2, minute=3,
                                                           second=4, microsecond=5)

        mock_client_instance = MagicMock()
        mock_client_instance.get_bucket.return_value = create_mock_bucket([
            (f'analyse-configuration.json', '{"model_blob_name": "fish"}')
        ])

        mock_client.return_value = mock_client_instance
        mock_event = MagicMock()
        mock_context = MagicMock()

        with mock.patch.dict(os.environ, {'SOURCES_BUCKET_NAME': 'rhubarb'}):
            response_json = main.process_scheduled(mock_event, mock_context)

        response = json.loads(response_json)

        self.assertEqual('OK', response['STATUS'])
        self.assertEqual({}, response['Counts'])

    @mock.patch('main.run_cloud_function_async_with_parameter_list')
    @mock.patch('google.cloud.storage.Client')
    @mock.patch('main.datetime')
    def test_each_data_blob_processed(self, mock_datetime, mock_client, mock_run_async):
        datetime_now = datetime.datetime(year=1999, month=1, day=1, hour=2, minute=3, second=4, microsecond=5)
        twenty_minutes_ago = datetime.datetime(year=1999, month=1, day=1, hour=1, minute=40, second=0, microsecond=0)
        mock_datetime.now.return_value = datetime_now

        mock_client_instance = MagicMock()
        model_blob_name = 'fish'
        mock_client_instance.get_bucket.return_value = create_mock_bucket([
            ('analyse-configuration.json', f'{{"model_blob_name": "{model_blob_name}"}}')
        ])

        mock_blob = MagicMock()
        data_root = 'Supplier'
        mock_blob.name = f'analyse/{data_root}.json'
        camera_id = 'camera1'
        mock_blob.download_as_string.return_value = f'["{camera_id}"]'
        mock_client_instance.list_blobs.return_value = [mock_blob]

        mock_client.return_value = mock_client_instance

        mock_run_async.return_value = [{"STATUS": "Processed"}]

        mock_event = MagicMock()
        mock_context = MagicMock()

        with mock.patch.dict(os.environ, {'SOURCES_BUCKET_NAME': 'rhubarb'}):
            response_json = main.process_scheduled(mock_event, mock_context)

        response = json.loads(response_json)

        self.assertEqual('OK', response['STATUS'])
        self.assertEqual({"Processed": 1}, response['Counts'])
        self.assertEqual(1, len(mock_run_async.call_args_list))
        self.assertEqual("data_blob_name", mock_run_async.call_args_list[0][1]['json_key'])
        self.assertEqual([f"{data_root}/{twenty_minutes_ago:%Y%m%d}/{twenty_minutes_ago:%H%M}/{camera_id}.jpg"], mock_run_async.call_args_list[0][1]['json_values'])
        self.assertEqual(model_blob_name, mock_run_async.call_args_list[0][1]['partial_json']['model_blob_name'])

    @mock.patch('main.run_cloud_function_async_with_parameter_list')
    @mock.patch('google.cloud.storage.Client')
    @mock.patch('main.datetime')
    @mock.patch('main.logging')
    def test_reported_errors_logged(self, mock_logging, mock_datetime, mock_client, mock_run_async):
        datetime_now = datetime.datetime(year=1999, month=1, day=1, hour=2, minute=3, second=4, microsecond=5)
        mock_datetime.now.return_value = datetime_now

        mock_client_instance = MagicMock()
        model_blob_name = 'fish'
        mock_client_instance.get_bucket.return_value = create_mock_bucket([
            ('analyse-configuration.json', f'{{"model_blob_name": "{model_blob_name}"}}')
        ])

        mock_blob = MagicMock()
        data_root = 'Supplier'
        mock_blob.name = f'analyse/{data_root}.json'
        camera_id = 'camera1'
        mock_blob.download_as_string.return_value = f'["{camera_id}"]'
        mock_client_instance.list_blobs.return_value = [mock_blob, mock_blob, mock_blob, mock_blob, mock_blob,
                                                        mock_blob, mock_blob, mock_blob]

        mock_client.return_value = mock_client_instance

        mock_run_async.return_value = [
            {"STATUS": "Processed"},
                                       {"STATUS": "uh oh how weird"},
                                       {"STATUS": "Faulty"},
                                       {"STATUS": "Missing"},
                                       {
                                           'STATUS': 'Errored',
                                           'Message': 'Forbidden - not authorised with "..."',
                                           'TextResponse': '',
                                           'JsonResponse': ''
                                       },
                                       {"STATUS": "Processed"},
                                       {
                                           'STATUS': 'Errored',
                                           'Message': 'Failed after 7 attempts with "dummy"',
                                           'TextResponse': '',
                                           'JsonResponse': ''
                                       },
                                       {"STATUS": "Processed"}
                                       ]

        mock_event = MagicMock()
        mock_context = MagicMock()

        with mock.patch.dict(os.environ, {'SOURCES_BUCKET_NAME': 'rhubarb'}):
            response_json = main.process_scheduled(mock_event, mock_context)

        response = json.loads(response_json)

        self.assertEqual('OK', response['STATUS'])
        self.assertEqual({"Processed": 3, "Faulty": 1, "Missing": 1, "Errored": 2, "uh oh how weird": 1},
                         response['Counts'])

        mock_logging.critical.assert_any_call('Incomplete execution - possible outage:'
                                              ' "Supplier/19990101/0140/camera1.jpg" result:'
                                              ' {\'STATUS\': \'Errored\','
                                              ' \'Message\': \'Forbidden - not authorised with "..."\','
                                              ' \'TextResponse\': \'\','
                                              ' \'JsonResponse\': \'\'}')
        mock_logging.critical.assert_any_call('Incomplete execution - possible outage:'
                                              ' "Supplier/19990101/0140/camera1.jpg" result:'
                                              ' {\'STATUS\': \'Errored\','
                                              ' \'Message\': \'Failed after 7 attempts with "dummy"\','
                                              ' \'TextResponse\': \'\','
                                              ' \'JsonResponse\': \'\'}')
        mock_logging.error.assert_any_call('Unexpected STATUS type: "uh oh how weird"')

    @mock.patch('main.run_cloud_function_async_with_parameter_list')
    @mock.patch('google.cloud.storage.Client')
    @mock.patch('main.datetime')
    def test_latest_newer_than_datetime_rounds_down_to_nearest_10_mins(self, mock_datetime, mock_client, mock_run_async):
        datetime_now = datetime.datetime(year=1999, month=1, day=1, hour=2, minute=3, second=4, microsecond=5)
        mock_datetime.now.return_value = datetime_now
        expected_20_minutes_ago = datetime.datetime(year=1999, month=1, day=1, hour=1, minute=40, second=0, microsecond=0)

        mock_client_instance = MagicMock()
        model_blob_name = 'fish'
        mock_client_instance.get_bucket.return_value = create_mock_bucket([
            ('analyse-configuration.json', f'{{"model_blob_name": "{model_blob_name}"}}')
        ])

        mock_blob = MagicMock()
        data_root = 'Supplier'
        mock_blob.name = f'analyse/{data_root}.json'
        camera_id = 'camera1'
        mock_blob.download_as_string.return_value = f'["{camera_id}"]'
        mock_client_instance.list_blobs.return_value = [mock_blob]

        mock_client.return_value = mock_client_instance

        mock_run_async.return_value = [{"STATUS": "Processed"}]

        mock_event = MagicMock()
        mock_context = MagicMock()

        with mock.patch.dict(os.environ, {'SOURCES_BUCKET_NAME': 'rhubarb'}):
            response_json = main.process_scheduled(mock_event, mock_context)

        response = json.loads(response_json)

        self.assertEqual('OK', response['STATUS'])
        self.assertEqual({"Processed": 1}, response['Counts'])
        self.assertEqual(1, len(mock_run_async.call_args_list))
        self.assertEqual("data_blob_name", mock_run_async.call_args_list[0][1]['json_key'])
        self.assertEqual([f"{data_root}/{expected_20_minutes_ago:%Y%m%d}/{expected_20_minutes_ago:%H%M}/{camera_id}.jpg"],
                         mock_run_async.call_args_list[0][1]['json_values'])
        self.assertEqual(model_blob_name, mock_run_async.call_args_list[0][1]['partial_json']['model_blob_name'])

    @mock.patch('main.run_cloud_function_async_with_parameter_list')
    @mock.patch('google.cloud.storage.Client')
    @mock.patch('main.datetime')
    def test_latest_newer_than_datetime_rounds_down_to_nearest_10_mins_given_current_time_already_at_10_minute_floor(
            self, mock_datetime, mock_client,mock_run_async):
        datetime_now = datetime.datetime(year=2000, month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        mock_datetime.now.return_value = datetime_now
        expected_20_minutes_ago = datetime.datetime(year=1999, month=12, day=31, hour=23, minute=40, second=0,
                                                    microsecond=0)

        mock_client_instance = MagicMock()
        model_blob_name = 'fish'
        mock_client_instance.get_bucket.return_value = create_mock_bucket([
            ('analyse-configuration.json', f'{{"model_blob_name": "{model_blob_name}"}}')
        ])

        mock_blob = MagicMock()
        data_root = 'Supplier'
        mock_blob.name = f'analyse/{data_root}.json'
        camera_id = 'camera1'
        mock_blob.download_as_string.return_value = f'["{camera_id}"]'
        mock_client_instance.list_blobs.return_value = [mock_blob]

        mock_client.return_value = mock_client_instance

        mock_run_async.return_value = [{"STATUS": "Processed"}]

        mock_event = MagicMock()
        mock_context = MagicMock()

        with mock.patch.dict(os.environ, {'SOURCES_BUCKET_NAME': 'rhubarb'}):
            response_json = main.process_scheduled(mock_event, mock_context)

        response = json.loads(response_json)

        self.assertEqual('OK', response['STATUS'])
        self.assertEqual({"Processed": 1}, response['Counts'])
        self.assertEqual(1, len(mock_run_async.call_args_list))
        self.assertEqual("data_blob_name", mock_run_async.call_args_list[0][1]['json_key'])
        self.assertEqual(
            [f"{data_root}/{expected_20_minutes_ago:%Y%m%d}/{expected_20_minutes_ago:%H%M}/{camera_id}.jpg"],
            mock_run_async.call_args_list[0][1]['json_values'])
        self.assertEqual(model_blob_name, mock_run_async.call_args_list[0][1]['partial_json']['model_blob_name'])
