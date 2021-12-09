import json
import os
from importlib import reload
from unittest import TestCase, mock
from unittest.mock import MagicMock

import google

with mock.patch('google.cloud.storage.Client'):
    with mock.patch('chrono_lens.gcloud.logging.setup_logging_and_trace'):
        import main  # Note this a bootstrap - we will force reload each test, after mocking environment variables


def create_mock_request(request_json):
    mock_request = MagicMock()
    mock_request.get_json = MagicMock(return_value=request_json)
    return mock_request


class TestCountObjectsEnvironmentVariableFailures(TestCase):
    """
    Note that importing "main" will only happen once - it will remain in cache; yet we want it reloaded as we
    are providing mocked environment variables.

    https://stackoverflow.com/questions/437589/how-do-i-unload-reload-a-python-module
    highlights that objects may hang around and not be reloaded cleanly; this behaviour was observed when using:
        if 'myModule' in sys.modules:
            del sys.modules["myModule"]

    Subsequently reading:
    https://stackoverflow.com/questions/437589/how-do-i-unload-reload-a-python-module/438845#438845
    now using the reload() functionality, each time initially importing main (to ensure it is present)
    then forcing a reload. Necessary as we do not know the order of importing...

    """

    def test_undefined_models_bucket_name(self):
        data_bucket_name = 'test_undefined_models_bucket_name=data_bucket'

        def fake_get_bucket(bucket_name):
            if bucket_name == data_bucket_name:
                return MagicMock

            raise google.api_core.exceptions.NotFound(bucket_name)

        mock_client_instance = MagicMock()
        mock_client_instance.get_bucket.side_effect = fake_get_bucket

        with mock.patch.dict(os.environ, {
            'DATA_BUCKET_NAME': data_bucket_name
        }):
            with mock.patch('google.cloud.storage.Client') as mocked_client:
                with mock.patch('chrono_lens.gcloud.logging.setup_logging_and_trace'):
                    mocked_client.return_value = mock_client_instance
                    reload(main)

        mock_request = create_mock_request({
            'image_blob_name': 'test_undefined_models_bucket_name=image_blob',
            'model_blob_name': 'test_undefined_models_bucket_name=model_blob',
        })

        response_json = main.count_objects(mock_request)
        response = json.loads(response_json)

        self.assertEqual('Errored', response['STATUS'])
        self.assertEqual('RuntimeError: "MODELS_BUCKET_NAME" not defined as an environment variable',
                         response['Message'])

    def test_undefined_data_bucket_name(self):
        models_bucket_name = 'test_undefined_data_bucket_name=models_bucket'

        def fake_get_bucket(bucket_name):
            if bucket_name == models_bucket_name:
                return MagicMock

            raise google.api_core.exceptions.NotFound(bucket_name)

        mock_client_instance = MagicMock()
        mock_client_instance.get_bucket.side_effect = fake_get_bucket

        with mock.patch.dict(os.environ, {
            'MODELS_BUCKET_NAME': models_bucket_name
        }):
            with mock.patch('google.cloud.storage.Client') as mocked_client:
                with mock.patch('chrono_lens.gcloud.logging.setup_logging_and_trace'):
                    mocked_client.return_value = mock_client_instance
                    reload(main)

        mock_request = create_mock_request({
            'image_blob_name': 'test_undefined_data_bucket_name=image_blob',
            'model_blob_name': 'test_undefined_data_bucket_name=model_blob',
        })

        response_json = main.count_objects(mock_request)
        response = json.loads(response_json)

        self.assertEqual('Errored', response['STATUS'])
        self.assertEqual('RuntimeError: "DATA_BUCKET_NAME" not defined as an environment variable',
                         response['Message'])

    def test_models_bucket_not_found(self):
        data_bucket_name = 'test_models_bucket_not_found=data_bucket'

        def fake_get_bucket(bucket_name):
            if bucket_name == data_bucket_name:
                return MagicMock

            raise google.api_core.exceptions.NotFound(bucket_name)

        mock_client_instance = MagicMock()
        mock_client_instance.get_bucket.side_effect = fake_get_bucket

        bogus_models_bucket_name = 'test_models_bucket_not_found=rhubarb'
        with mock.patch.dict(os.environ, {
            'DATA_BUCKET_NAME': data_bucket_name,
            'MODELS_BUCKET_NAME': bogus_models_bucket_name
        }):
            with mock.patch('google.cloud.storage.Client') as mocked_client:
                with mock.patch('chrono_lens.gcloud.logging.setup_logging_and_trace'):
                    mocked_client.return_value = mock_client_instance
                    reload(main)

        mock_request = create_mock_request({
            'image_blob_name': 'test_models_bucket_not_found=image_blob',
            'model_blob_name': 'test_models_bucket_not_found=model_blob',
        })

        response_json = main.count_objects(mock_request)
        response = json.loads(response_json)

        self.assertEqual('Errored', response['STATUS'])
        self.assertEqual(f'RuntimeError: Google bucket name "{bogus_models_bucket_name}"'
                         ' (used for "models_bucket_name")'
                         ' failed to open a bucket',
                         response['Message'])

    def test_data_bucket_not_found(self):
        models_bucket_name = 'test_data_bucket_not_found=models_bucket'

        def fake_get_bucket(bucket_name):
            if bucket_name == models_bucket_name:
                return MagicMock

            raise google.api_core.exceptions.NotFound(bucket_name)

        mock_client_instance = MagicMock()
        mock_client_instance.get_bucket.side_effect = fake_get_bucket

        bogus_data_bucket_name = 'test_data_bucket_not_found=rhubarb'
        with mock.patch.dict(os.environ, {
            'DATA_BUCKET_NAME': bogus_data_bucket_name,
            'MODELS_BUCKET_NAME': models_bucket_name
        }):
            with mock.patch('google.cloud.storage.Client') as mocked_client:
                with mock.patch('chrono_lens.gcloud.logging.setup_logging_and_trace'):
                    mocked_client.return_value = mock_client_instance
                    reload(main)

        mock_request = create_mock_request({
            'image_blob_name': 'test_data_bucket_not_found=image_blob',
            'model_blob_name': 'test_data_bucket_not_found=model_blob',
        })

        response_json = main.count_objects(mock_request)
        response = json.loads(response_json)

        self.assertEqual('Errored', response['STATUS'])
        self.assertEqual(f'RuntimeError: Google bucket name "{bogus_data_bucket_name}" (used for "data_bucket_name")'
                         ' failed to open a bucket',
                         response['Message'])
