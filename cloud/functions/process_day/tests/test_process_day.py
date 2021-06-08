import datetime
import json
import os
from unittest import TestCase, mock
from unittest.mock import MagicMock

function_region = 'somewhere-safe'
gcp_project = 'our-project'
data_bucket_name = 'dummy-data-bucket'
# We mock "os" before importing "main", as there is code outside of functions that will execute on import
# rather than on function call - hence we need to get in before code is imported
with mock.patch.dict(os.environ, {
    'FUNCTION_REGION': function_region,
    'GCP_PROJECT': gcp_project,
    'DATA_BUCKET_NAME': data_bucket_name
}):
    with mock.patch('google.cloud.bigquery.Client') as mock_big_query_client_constructor:
        mock_big_query_client = MagicMock()
        mock_big_query_client_constructor.return_value = mock_big_query_client

        with mock.patch('google.cloud.storage.Client') as mock_storage_client_constructor:
            mock_storage_client = MagicMock()
            mock_storage_client_constructor.return_value = mock_storage_client

            with mock.patch('dsc_lib.gcloud.logging.setup_logging_and_trace'):
                from main import process_day


"""
Example JSON test:
{
    "date_to_process": "20201224",
    "camera_id": "00001.01234"
}
"""


def create_mock_request(request_json):
    mock_request = MagicMock()
    mock_request.get_json = MagicMock(return_value=request_json)
    return mock_request


class TestProcessDay(TestCase):

    def test_missing_date_to_process(self):
        mock_request = create_mock_request({})

        response_json = process_day(mock_request)
        response = json.loads(response_json)

        self.assertEqual('Errored', response['STATUS'])
        self.assertEqual('RuntimeError: "date_to_process" not defined via JSON or arguments in http header',
                         response['Message'])

    def test_missing_camera_id_to_process(self):
        mock_request = create_mock_request({
            "date_to_process": "20200103"
        })

        response_json = process_day(mock_request)
        response = json.loads(response_json)

        self.assertEqual('Errored', response['STATUS'])
        self.assertEqual('RuntimeError: "camera_id" not defined via JSON or arguments in http header',
                         response['Message'])

    def test_missing_data_root_to_process(self):
        mock_request = create_mock_request({
            "date_to_process": "20200103",
            "camera_id": "123.456"
        })

        response_json = process_day(mock_request)
        response = json.loads(response_json)

        self.assertEqual('Errored', response['STATUS'])
        self.assertEqual('RuntimeError: "data_root" not defined via JSON or arguments in http header',
                         response['Message'])

    def test_missing_model_blob_name_to_process(self):
        mock_request = create_mock_request({
            "date_to_process": "20200103",
            "camera_id": "123.456",
            "data_root": "a-source"
        })

        response_json = process_day(mock_request)
        response = json.loads(response_json)

        self.assertEqual('Errored', response['STATUS'])
        self.assertEqual('RuntimeError: "model_blob_name" not defined via JSON or arguments in http header',
                         response['Message'])

    def test_invalid_date_to_process(self):
        mock_request = create_mock_request({
            "date_to_process": "test",
            "camera_id": "123.456",
            "data_root": "a-source",
            "model_blob_name": "a-model"
        })

        response_json = process_day(mock_request)
        response = json.loads(response_json)

        self.assertEqual('Errored', response['STATUS'])
        self.assertEqual('ValueError: "date_to_process" incorrect format (received "test", expected "YYYYMMDD")',
                         response['Message'])

    def test_incorrect_format_date_to_process(self):
        mock_request = create_mock_request({
            "date_to_process": "24032020",
            "camera_id": "123.456",
            "data_root": "a-source",
            "model_blob_name": "a-model"
        })

        response_json = process_day(mock_request)
        response = json.loads(response_json)

        self.assertEqual('Errored', response['STATUS'])
        self.assertEqual('ValueError: "date_to_process" incorrect format (received "24032020", expected "YYYYMMDD")',
                         response['Message'])

    @mock.patch('dsc_lib.gcloud.async_functions.aiohttp')
    @mock.patch('dsc_lib.gcloud.authentication.requests')
    def test_requests_process_for_every_10_mins_with_unknown_data_root_returns_error(
            self, _mock_requests, mock_aiohttp):
        expected_data_root = "a-source"
        mock_request = create_mock_request({
            "date_to_process": "20200101",
            "camera_id": "123.456",
            "data_root": expected_data_root,
            "model_blob_name": "a-model"
        })

        def mock_list_blobs(bucket, max_results, prefix):
            if prefix == expected_data_root:
                return []
            return ['1']

        mock_storage_client.list_blobs.side_effect = mock_list_blobs

        response_json = process_day(mock_request)
        response = json.loads(response_json)

        self.assertEqual('Errored', response['STATUS'])
        self.assertEqual(f'ValueError: "{expected_data_root}" does not exist within bucket "{data_bucket_name}"',
                         response['Message'])

    @mock.patch('dsc_lib.gcloud.async_functions.aiohttp')
    @mock.patch('dsc_lib.gcloud.authentication.requests')
    def test_requests_process_for_every_10_mins_with_known_data_root_but_missing_date_returns_error(
            self, _mock_requests, mock_aiohttp):
        expected_data_root = "a-source"
        date_to_process_raw = "20200101"
        mock_request = create_mock_request({
            "date_to_process": date_to_process_raw,
            "camera_id": "123.456",
            "data_root": expected_data_root,
            "model_blob_name": "a-model"
        })

        def mock_list_blobs(bucket_or_name, max_results, prefix):
            if prefix == expected_data_root:
                return [f'{expected_data_root}/19990101/0000/widget.jpg']
            elif prefix == f'{expected_data_root}/{date_to_process_raw}':
                return []
            return ['1']

        mock_storage_client.list_blobs.side_effect = mock_list_blobs

        response_json = process_day(mock_request)
        response = json.loads(response_json)

        self.assertEqual('Errored', response['STATUS'])
        self.assertEqual(f'ValueError: "{expected_data_root}" does not have "{date_to_process_raw}" present within bucket "{data_bucket_name}"',
            response['Message'])

    @mock.patch('dsc_lib.gcloud.async_functions.aiohttp')
    @mock.patch('dsc_lib.gcloud.authentication.requests')
    def test_requests_process_for_every_10_mins_with_one_already_processed_with_duplicates(
            self, _mock_requests, mock_aiohttp):
        # @todo test can realistically be reduced to mocking run_cloud_function_async_with_parameter_list
        expected_cloud_function_end_point = f'https://{function_region}-{gcp_project}.cloudfunctions.net' \
            '/run_model_on_image'

        expected_date_to_process = "20200304"
        expected_model_blob_name = "a-model"
        expected_table_name = "amodel"
        expected_data_source = "data-source"
        expected_preprocessed_time = datetime.time(10, 20)

        camera_id = "sample_image"
        expected_image_name = camera_id + ".jpg"
        mock_request = create_mock_request({
            "date_to_process": expected_date_to_process,
            "camera_id": camera_id,
            "data_root": expected_data_source,
            "model_blob_name": expected_model_blob_name
        })

        success_text = "Processed"

        class MockResponse:
            def __init__(self, status, response_text):
                self.status = status
                self.response_text = response_text

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc_val, exc_tb):
                return

            async def text(self):
                return self.response_text

        failures_to_trigger = 2

        class MockSession:
            def __init__(self):
                self.calls_made = []
                self.failures_to_trigger = failures_to_trigger

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc_val, exc_tb):
                return

            async def post(self, url, json):
                self.calls_made.append((url, json['data_blob_name'], json['model_blob_name']))
                if self.failures_to_trigger > 0:
                    self.failures_to_trigger -= 1
                    return MockResponse(404, '{"STATUS": "Boom!", "Message": "ValueError: sorry about that"}')
                return MockResponse(200, f'{{"STATUS": "{success_text}"}}')

        mock_session = MockSession()
        mock_aiohttp.ClientSession.return_value = mock_session

        # Fake that one entry has already been processed - but add in a duplicate as if we have accidentally
        # processed twice
        mock_table = MagicMock()
        mock_table.table_id = expected_table_name

        mock_query_job = MagicMock()
        mock_query_job.result.return_value = [
            {'time': expected_preprocessed_time},
            {'time': expected_preprocessed_time}
        ]

        mock_big_query_client.list_tables.return_value = [mock_table]
        mock_big_query_client.query.return_value = mock_query_job

        mock_storage_client.list_blobs.return_value = [expected_data_source]

        results_json = process_day(mock_request)
        results = json.loads(results_json)

        self.assertEqual("OK", results['STATUS'])
        self.assertEqual((24 * 6) - 1, results['Counts'][success_text])
        self.assertEqual(1, results['Counts'][
            'Already Processed'])  # Duplicate entry in BigQuery should only count as 1 already processed image

        # ... assert calls made to async http ...
        times_to_request = [f'{hour:02}{minute:02}' for hour in range(0, 24) for minute in range(0, 60, 10)]

        # first 2 calls will trigger failure... so their times will appear twice
        times_to_request.append('0000')
        times_to_request.append('0010')

        # 1 call removed as detected as already processed
        times_to_request.remove(f'{expected_preprocessed_time:%H%M}')

        for call_made in mock_session.calls_made:
            self.assertEqual(expected_cloud_function_end_point, call_made[0])
            path_parts = call_made[1].split('/')
            self.assertEqual(expected_data_source, path_parts[0])
            self.assertIn(path_parts[2], times_to_request)
            times_to_request.remove(path_parts[2])
            self.assertEqual(expected_date_to_process, path_parts[1])
            self.assertEqual(expected_image_name, path_parts[3])
            self.assertEqual(expected_model_blob_name, call_made[2])

        self.assertEqual(0, len(times_to_request))

    @mock.patch('main.run_cloud_function_async_with_parameter_list')
    @mock.patch('dsc_lib.gcloud.async_functions.aiohttp')
    @mock.patch('dsc_lib.gcloud.authentication.requests')
    @mock.patch('main.logging')
    def test_logs_all_failing_calls(
            self, mock_logging, _mock_requests, mock_aiohttp, mock_run_async):

        expected_date_to_process = "20200304"
        expected_model_blob_name = "a-model"
        expected_table_name = "amodel"
        expected_data_source = "data-source"
        expected_preprocessed_time = datetime.time(10, 20)

        camera_id = "sample_image"
        mock_request = create_mock_request({
            "date_to_process": expected_date_to_process,
            "camera_id": camera_id,
            "data_root": expected_data_source,
            "model_blob_name": expected_model_blob_name
        })

        # Fake that one entry has already been processed
        # processed twice
        mock_table = MagicMock()
        mock_table.table_id = expected_table_name

        mock_query_job = MagicMock()
        mock_query_job.result.return_value = [
            {'time': expected_preprocessed_time}
        ]

        mock_big_query_client.list_tables.return_value = [mock_table]
        mock_big_query_client.query.return_value = mock_query_job

        mock_storage_client.list_blobs.return_value = [expected_data_source]

        mock_run_async.return_value = [{"STATUS": "Processed"},
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

        response_json = process_day(mock_request)
        response = json.loads(response_json)

        self.assertEqual('OK', response['STATUS'])
        self.assertEqual(
            {"Already Processed": 1, "Processed": 3, "Faulty": 1, "Missing": 1, "Errored": 2, "uh oh how weird": 1},
            response['Counts'])

        mock_logging.critical.assert_any_call('Incomplete execution - possible outage;'
                                              ' "data-source/20200304/0040/sample_image.jpg" result:'
                                              ' {\'STATUS\': \'Errored\','
                                              ' \'Message\': \'Forbidden - not authorised with "..."\','
                                              ' \'TextResponse\': \'\','
                                              ' \'JsonResponse\': \'\'}')
        mock_logging.critical.assert_any_call('Incomplete execution - possible outage;'
                                              ' "data-source/20200304/0100/sample_image.jpg" result:'
                                              ' {\'STATUS\': \'Errored\','
                                              ' \'Message\': \'Failed after 7 attempts with "dummy"\','
                                              ' \'TextResponse\': \'\','
                                              ' \'JsonResponse\': \'\'}')
        mock_logging.error.assert_any_call('Unexpected STATUS type: "uh oh how weird"')
