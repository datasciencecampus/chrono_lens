import unittest

import pytest
from mock import patch, MagicMock

from tests.chrono_lens.gcloud.filters import is_running_on_gcp

if is_running_on_gcp():
    from scripts.gcloud import download_analysis_camera_list
else:
    pytestmark = pytest.mark.skip(reason="Skipping as not running on GCP")


@patch('scripts.download_analysis_camera_list.dump')
@patch('scripts.download_analysis_camera_list.storage')
class TestDownloadAnalysisCameraList(unittest.TestCase):
    def test_pulls_blobs_and_extracts_camera_name(self, mock_storage, mock_json_dump):
        mock_client = MagicMock()
        mock_storage.Client.from_service_account_json.return_value = mock_client

        mock_camera_names_blob = MagicMock()
        camera_names_blob_name = 'analyse/my-images.json'
        camera_names_blob_content_as_string = '["camera1", "camera2"]'
        mock_camera_names_blob.name = camera_names_blob_name
        mock_camera_names_blob.download_as_string.return_value = camera_names_blob_content_as_string

        mock_other_blob = MagicMock()
        mock_other_blob.name = 'analyse/my-images.rhubarb'

        mock_client.list_blobs.return_value = [mock_other_blob, mock_camera_names_blob]

        expected_model_config_name = 'FaultyImageFilterV1_NewcastleV2_StaticObjectFilterV3'

        model_config_as_string = f'{{"model_blob_name": "{expected_model_config_name}"}}'

        mock_model_blob = MagicMock()
        mock_model_blob.download_as_string.return_value = model_config_as_string

        mock_bucket = MagicMock()
        mock_bucket.blob.return_value = mock_model_blob

        mock_client.bucket.return_value = mock_bucket

        expected_camera_sources = {'my-images': ['camera1', 'camera2']}
        command_line_args = [
            '--cameras-to-analyse-file=camera-to-analyse.json',
            '--model-config-file=model-config.txt',
            '--JSON-private-key=JWT.json'
        ]

        class fake_open:
            def __init__(self):
                self.text = ""

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc_val, exc_tb):
                pass

            def write(self, text):
                self.text += text

        fake_open_instance = fake_open()

        # mock_json.dump.side_effect = fake_json_dump

        mock_open = MagicMock()
        with patch('builtins.open', mock_open):
            mock_open.return_value = fake_open_instance

            download_analysis_camera_list.main(command_line_args)

        mock_json_dump.assert_called_once_with(
            expected_camera_sources, fake_open_instance, indent=4, sort_keys=True
        )

        self.assertEqual(expected_model_config_name, fake_open_instance.text)
