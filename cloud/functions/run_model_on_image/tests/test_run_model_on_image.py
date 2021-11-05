import json
import os
from unittest import TestCase
from unittest import mock

gcp_region = 'somewhere-safe'
gcp_project = 'our-project'

with mock.patch('google.cloud.storage.blob') as mocked_storage_blob:
    with mock.patch('chrono_lens.gcloud.logging.setup_logging_and_trace'):
        with mock.patch.dict(os.environ, {
            'FUNCTION_REGION': gcp_region,
            'GCP_PROJECT': gcp_project
        }):
            import main

valid_model_blob_name = 'actual/model.pb'
valid_data_blob_name = 'source/data/time/img.jpg'
map_json_and_endpoint_to_response = {}
logged_run_cloud_function_async_with_parameter_list_calls = []


def create_mock_request(request_json):
    mock_request = mock.MagicMock()
    mock_request.get_json = mock.MagicMock(return_value=request_json)
    return mock_request


def mocked_run_cloud_function_async_with_parameter_list(json_key, json_values, partial_json, endpoint, headers=None,
                                                        sleep_base=16, sleep_tuple=(1, 16)):
    assert (json_key, endpoint) in map_json_and_endpoint_to_response, f"({json_key}, {endpoint}) not mocked"
    logged_run_cloud_function_async_with_parameter_list_calls.append(
        {'json_key': json_key, 'json_values': json_values, 'partial_json': partial_json, 'endpoint': endpoint,
         'headers': headers, 'sleep_base': sleep_base, 'sleep_tuple': sleep_tuple}
    )
    return [map_json_and_endpoint_to_response[(json_key, endpoint)]]


# This method will be used by the mock to replace get_token_header
def mocked_create_authenticated_cloud_function_headers(_args):
    return 'token'


def mocked_blob(name, bucket):
    class MockedBlob:
        def __init__(self, blob_name, blob_bucket):
            self.name = blob_name
            self.bucket = blob_bucket

        def exists(self):
            return self.name == valid_data_blob_name

    return MockedBlob(name, bucket)


@mock.patch('google.cloud.storage.blob.Blob', side_effect=mocked_blob)
@mock.patch('main.run_cloud_function_async_with_parameter_list',
            side_effect=mocked_run_cloud_function_async_with_parameter_list)
class TestRunModelOnImage(TestCase):
    def test_missing_data_blob_name_raises_error(self, _mocked_cloud_func, _mocked_blob):
        mock_request = create_mock_request({})

        response_json = main.run_model_on_image(mock_request)
        response = json.loads(response_json)

        self.assertEqual('Errored', response['STATUS'])
        self.assertEqual('RuntimeError: "data_blob_name" not defined via JSON or arguments in http header',
                         response['Message'])

    def test_missing_model_blob_name_raises_error(self, _mocked_cloud_func, _mocked_blob):
        mock_request = create_mock_request({
            'data_blob_name': 'test_image_bucket'
        })

        response_json = main.run_model_on_image(mock_request)
        response = json.loads(response_json)

        self.assertEqual('Errored', response['STATUS'])
        self.assertEqual('RuntimeError: "model_blob_name" not defined via JSON or arguments in http header',
                         response['Message'])

    def test_reported_if_object_count_request_raises_error(self, _mocked_cloud_func, _mocked_blob):
        mocked_storage_blob.Blob = mocked_blob
        invalid_model_blob_name = 'false/model.pb'
        invalid_params = {
            'data_blob_name': valid_data_blob_name,
            'model_blob_name': invalid_model_blob_name
        }

        mock_request = create_mock_request(invalid_params)
        global map_json_and_endpoint_to_response
        map_json_and_endpoint_to_response = {
            ('image_blob_name', f'https://{gcp_region}-{gcp_project}.cloudfunctions.net/count_objects'): {
                'STATUS': 'Errored',
                'Message': f'RuntimeError, sorry about that',
                'Arguments': {'A': 'B'}
            }
        }
        response_json = main.run_model_on_image(mock_request)
        response = json.loads(response_json)

        self.assertEqual('Errored', response['STATUS'])
        self.assertEqual('RuntimeError: object_count request reported "Errored": "{\'STATUS\': \'Errored\','
                         ' \'Message\': \'RuntimeError, sorry about that\', \'Arguments\': {\'A\': \'B\'}}"',
                         response['Message'])

    def test_reported_if_object_count_request_failed_to_respond(self, _mocked_cloud_func, _mocked_blob):
        valid_params = {
            'data_blob_name': valid_data_blob_name,
            'model_blob_name': valid_model_blob_name
        }

        mock_request = create_mock_request(valid_params)
        global map_json_and_endpoint_to_response
        map_json_and_endpoint_to_response = {
            ('image_blob_name', f'https://{gcp_region}-{gcp_project}.cloudfunctions.net/count_objects'): {
                'STATUS': 'Errored',
                'Message': f'Failed after 5 attempts with "image_blob_name"',
                'TextResponse': 'boo',
                'JsonResponse': {1: 2}
            }
        }
        response_json = main.run_model_on_image(mock_request)
        response = json.loads(response_json)

        self.assertEqual('Errored', response['STATUS'])
        self.assertEqual('ConnectionError: object_count request reported "Errored": "{\'STATUS\': \'Errored\','
                         ' \'Message\': \'Failed after 5 attempts with "image_blob_name"\', \'TextResponse\': \'boo\','
                         ' \'JsonResponse\': {1: 2}}"',
                         response['Message'])

    def test_valid_params_to_object_count_and_passes_results_to_bigquery_write(self, _mocked_cloud_func,
                                                                               _mocked_blob):
        valid_params = {
            'data_blob_name': valid_data_blob_name,
            'model_blob_name': valid_model_blob_name
        }

        bigquery_endpoint = f'https://{gcp_region}-{gcp_project}.cloudfunctions.net/bigquery_write'
        mock_request = create_mock_request(valid_params)
        global map_json_and_endpoint_to_response
        model_results = {'cars': 2, 'faulty': False, 'missing': False}
        map_json_and_endpoint_to_response = {
            ('image_blob_name', f'https://{gcp_region}-{gcp_project}.cloudfunctions.net/count_objects'): {
                'STATUS': 'Processed',
                'Message': f'All good',
                'results': model_results
            },
            ('image_blob_name', bigquery_endpoint): {
                'STATUS': 'Processed',
                'Message': f'All good'
            }
        }

        logged_run_cloud_function_async_with_parameter_list_calls.clear()
        response_json = main.run_model_on_image(mock_request)
        response = json.loads(response_json)

        self.assertEqual('Processed', response['STATUS'])
        self.assertEqual(bigquery_endpoint, logged_run_cloud_function_async_with_parameter_list_calls[1]['endpoint'])
        self.assertEqual(
            json.dumps(model_results),
            logged_run_cloud_function_async_with_parameter_list_calls[1]['partial_json']['model_results_json']
        )

    def test_valid_params_but_object_count_fails_reports_error(self, _mocked_cloud_func, _mocked_blob):
        valid_params = {
            'data_blob_name': valid_data_blob_name,
            'model_blob_name': valid_model_blob_name
        }

        mock_request = create_mock_request(valid_params)
        global map_json_and_endpoint_to_response
        error_status = 'Errored'
        error_message = 'RuntimeError, sorry about that'
        map_json_and_endpoint_to_response = {
            ('image_blob_name', f'https://{gcp_region}-{gcp_project}.cloudfunctions.net/count_objects'): {
                'STATUS': error_status,
                'Message': error_message,
                'Arguments': {'A': 'B'}
            }
        }

        response_json = main.run_model_on_image(mock_request)
        response = json.loads(response_json)

        self.assertEqual(error_status, response['STATUS'])
        self.assertEqual(f'RuntimeError: object_count request reported "{error_status}":'
                         f' "{{\'STATUS\': \'{error_status}\', \'Message\': \'{error_message}\','
                         f' \'Arguments\': {{\'A\': \'B\'}}}}"', response['Message'])

    def test_valid_params_but_bigquery_write_fails_reports_error(self, _mocked_cloud_func, _mocked_blob):
        valid_params = {
            'data_blob_name': valid_data_blob_name,
            'model_blob_name': valid_model_blob_name
        }

        mock_request = create_mock_request(valid_params)
        global map_json_and_endpoint_to_response
        error_status = 'Errored'
        error_message = 'RuntimeError, sorry about that'

        map_json_and_endpoint_to_response = {
            ('image_blob_name', f'https://{gcp_region}-{gcp_project}.cloudfunctions.net/count_objects'): {
                'STATUS': 'Processed',
                'Message': f'All good',
                'results': {'cars': 2, 'faulty': False, 'missing': False}
            },
            ('image_blob_name', f'https://{gcp_region}-{gcp_project}.cloudfunctions.net/bigquery_write'): {
                'STATUS': error_status,
                'Message': error_message,
                'Arguments': {'ouch': 'again'}
            }
        }

        response_json = main.run_model_on_image(mock_request)
        response = json.loads(response_json)

        self.assertEqual(error_status, response['STATUS'])
        self.assertEqual(f'RuntimeError: bigquery_write request reported "{error_status}":'
                         f' "{{\'STATUS\': \'{error_status}\', \'Message\': \'{error_message}\','
                         f' \'Arguments\': {{\'ouch\': \'again\'}}}}"', response['Message'])

    def test_valid_params_but_bigquery_write_fails_to_respond_reports_error(self, _mocked_cloud_func, _mocked_blob):
        valid_params = {
            'data_blob_name': valid_data_blob_name,
            'model_blob_name': valid_model_blob_name
        }

        mock_request = create_mock_request(valid_params)
        global map_json_and_endpoint_to_response
        error_status = 'Errored'
        error_message = 'Failed after 5 attempts with "image_blob_name"'
        map_json_and_endpoint_to_response = {
            ('image_blob_name', f'https://{gcp_region}-{gcp_project}.cloudfunctions.net/count_objects'): {
                'STATUS': 'Processed',
                'Message': f'All good',
                'results': {'cars': 2, 'faulty': False, 'missing': False}
            },
            ('image_blob_name', f'https://{gcp_region}-{gcp_project}.cloudfunctions.net/bigquery_write'): {
                'STATUS': error_status,
                'Message': error_message,
                'TextResponse': 'oh dear',
                'JsonResponse': {3: 4}
            }
        }

        response_json = main.run_model_on_image(mock_request)
        response = json.loads(response_json)

        self.assertEqual(error_status, response['STATUS'])
        self.assertEqual(f'ConnectionError: bigquery_write request reported "{error_status}":'
                         f' "{{\'STATUS\': \'{error_status}\', \'Message\': \'{error_message}\','
                         ' \'TextResponse\': \'oh dear\', \'JsonResponse\': {3: 4}}"',
                         response['Message'])
