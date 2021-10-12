import datetime
import unittest

import pytest
from mock import patch, MagicMock

from chrono_lens.exceptions import ProcessImagesException
from tests.chrono_lens.gcloud.filters import is_running_on_gcp

if is_running_on_gcp():
    from scripts.gcloud import batch_process_images
else:
    pytestmark = pytest.mark.skip(reason="Skipping as not running on GCP")


class TestBatchProcessImages(unittest.TestCase):
    def test_start_date_incorrect_format(self):
        command_line_args = [
            '--JSON-private-key=somefile.json',
            '--start-date=fish',
            '--end-date=20200202',
            '--cameras-json=testfile.json',
            '--model-name=FaultyImageFilterV0_NewcastleV0_StaticObjectFilterV0'
        ]

        self.assertRaisesRegex(ProcessImagesException, 'Start date not in format "YYYYMMDD" or invalid date',
                               batch_process_images.main, command_line_args)

    def test_start_date_invalid(self):
        command_line_args = [
            '--JSON-private-key=somefile.json',
            '--start-date=20202020',
            '--end-date=202002202',
            '--cameras-json=testfile.json',
            '--model-name=FaultyImageFilterV0_NewcastleV0_StaticObjectFilterV0'
        ]

        self.assertRaisesRegex(ProcessImagesException, 'Start date not in format "YYYYMMDD" or invalid date',
                               batch_process_images.main, command_line_args)

    def test_start_date_invalid_too_short(self):
        command_line_args = [
            '--JSON-private-key=somefile.json',
            '--start-date=2020220',
            '--end-date=20200221',
            '--cameras-json=testfile.json',
            '--model-name=FaultyImageFilterV0_NewcastleV0_StaticObjectFilterV0'
        ]

        self.assertRaisesRegex(ProcessImagesException, 'Start date not in format "YYYYMMDD" or invalid date',
                               batch_process_images.main, command_line_args)

    def test_end_date_incorrect_format(self):
        command_line_args = [
            '--JSON-private-key=somefile.json',
            '--start-date=19991220',
            '--end-date=fishier',
            '--cameras-json=testfile.json',
            '--model-name=FaultyImageFilterV0_NewcastleV0_StaticObjectFilterV0'
        ]

        self.assertRaisesRegex(ProcessImagesException, 'End date not in format "YYYYMMDD" or invalid date',
                               batch_process_images.main, command_line_args)

    def test_end_date_invalid(self):
        command_line_args = [
            '--JSON-private-key=somefile.json',
            '--start-date=19911201',
            '--end-date=20200132',
            '--cameras-json=testfile.json',
            '--model-name=FaultyImageFilterV0_NewcastleV0_StaticObjectFilterV0'
        ]

        self.assertRaisesRegex(ProcessImagesException, 'End date not in format "YYYYMMDD" or invalid date',
                               batch_process_images.main, command_line_args)

    def test_end_date_invalid_too_short(self):
        command_line_args = [
            '--JSON-private-key=somefile.json',
            '--start-date=20201201',
            '--end-date=2020022',
            '--cameras-json=testfile.json',
            '--model-name=FaultyImageFilterV0_NewcastleV0_StaticObjectFilterV0'
        ]

        self.assertRaisesRegex(ProcessImagesException, 'End date not in format "YYYYMMDD" or invalid date',
                               batch_process_images.main, command_line_args)

    def test_start_date_after_end_date(self):
        command_line_args = [
            '--JSON-private-key=somefile.json',
            '--start-date=19911202',
            '--end-date=19911201',
            '--cameras-json=testfile.json',
            '--model-name=FaultyImageFilterV0_NewcastleV0_StaticObjectFilterV0'
        ]

        self.assertRaisesRegex(ProcessImagesException, 'Start date after end date',
                               batch_process_images.main, command_line_args)

    def test_cannot_open_images_json_file(self):
        json_file_name = 'testfile.json'
        command_line_args = [
            '--JSON-private-key=somefile.json',
            '--start-date=19911201',
            '--end-date=19911201',
            f'--cameras-json={json_file_name}',
            '--model-name=FaultyImageFilterV0_NewcastleV0_StaticObjectFilterV0'
        ]

        mock = MagicMock()
        with patch('builtins.open', mock):
            mock.side_effect = IOError("No such file")
            self.assertRaisesRegex(ProcessImagesException,
                                   f'Failed to read camera IDs from JSON file "{json_file_name}"',
                                   batch_process_images.main, command_line_args)

    @patch('scripts.batch_process_images.json')
    @patch('scripts.batch_process_images.process_images')
    @patch('scripts.batch_process_images.logging')
    def test_all_args_correct(self, _mock_logging, mock_process_images, mock_json):
        json_file_name = 'testfile.json'
        cameras_to_analyse = {
            'test': ['a', 'b']
        }
        json_key_path = 'TOKENMAGIC.json'
        expected_date_str = '19911201'
        expected_date = datetime.datetime.strptime(expected_date_str, '%Y%m%d').date()
        expected_gcp_region = 'europe-west2'
        expected_gcp_project = 'unittest-project'
        command_line_args = [
            f'--JSON-private-key={json_key_path}',
            f'--start-date={expected_date_str}',
            f'--end-date={expected_date_str}',
            f'--cameras-json={json_file_name}',
            f'--gcp-project={expected_gcp_project}',
            f'--gcp-region={expected_gcp_region}',
            '--model-name=NewcastleV0'
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

        file_dictionary = {fake_open_instance: cameras_to_analyse}
        mock_json.load.side_effect = file_dictionary.get

        mock_process_images.run_model_on_images.return_value = {'Succeeded': 100}, [
            {'STATUS': 'Errored', 'Message': "sorry!"}]

        mock_open = MagicMock()
        with patch('builtins.open', mock_open):
            mock_open.return_value = fake_open_instance

            batch_process_images.main(command_line_args)

        mock_process_images.run_model_on_images.assert_called_once_with(
            start_date=expected_date,
            end_date=expected_date,
            json_key_path=json_key_path,
            model_blob_name='NewcastleV0',
            cameras_to_analyse=cameras_to_analyse,
            gcp_region=expected_gcp_region,
            gcp_project=expected_gcp_project
        )

    @patch('scripts.batch_process_images.json')
    @patch('scripts.batch_process_images.process_images')
    @patch('scripts.batch_process_images.date')
    @patch('scripts.batch_process_images.logging')
    def test_no_start_or_end_date_assumes_yesterday(self, _mock_logging, mock_date, mock_process_images, mock_json):
        json_file_name = 'testfile.json'
        cameras_to_analyse = {
            'test': ['a', 'b']
        }
        json_key_path = 'TOKENMAGIC.json'

        today = datetime.date(year=2000, month=10, day=20)
        yesterday = datetime.date(year=2000, month=10, day=19)
        mock_date.today.return_value = today

        expected_gcp_region = 'europe-west2'
        expected_gcp_project = 'traffic-cam-unittest'
        command_line_args = [
            f'--JSON-private-key={json_key_path}',
            f'--cameras-json={json_file_name}',
            f'--gcp-project={expected_gcp_project}',
            f'--gcp-region={expected_gcp_region}',
            '--model-name=NewcastleV0_StaticObjectFilterV0'
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

        file_dictionary = {fake_open_instance: cameras_to_analyse}
        mock_json.load.side_effect = file_dictionary.get

        mock_process_images.run_model_on_images.return_value = {'Succeeded': 100}, [
            {'STATUS': 'Errored', 'Message': "sorry!"}]

        mock_open = MagicMock()
        with patch('builtins.open', mock_open):
            mock_open.return_value = fake_open_instance

            batch_process_images.main(command_line_args)

        mock_process_images.run_model_on_images.assert_called_once_with(
            start_date=yesterday,
            end_date=yesterday,
            json_key_path=json_key_path,
            model_blob_name='NewcastleV0_StaticObjectFilterV0',
            cameras_to_analyse=cameras_to_analyse,
            gcp_region=expected_gcp_region,
            gcp_project=expected_gcp_project
        )

    @patch('scripts.batch_process_images.json')
    @patch('scripts.batch_process_images.process_images')
    @patch('scripts.batch_process_images.date')
    def test_no_start_or_end_date_assumes_yesterday(self, mock_date, mock_process_images, mock_json):
        json_file_name = 'testfile.json'
        cameras_to_analyse = {
            'test': ['a', 'b']
        }
        json_key_path = 'TOKENMAGIC.json'

        today = datetime.date(year=2000, month=10, day=20)
        yesterday = datetime.date(year=2000, month=10, day=19)
        mock_date.today.return_value = today

        expected_gcp_region = 'europe-west2'
        expected_gcp_project = 'unittest-project'
        command_line_args = [
            f'--JSON-private-key={json_key_path}',
            f'--cameras-json={json_file_name}',
            f'--gcp-project={expected_gcp_project}',
            f'--gcp-region={expected_gcp_region}',
            '--model-name=NewcastleV0_StaticObjectFilterV0'
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

        file_dictionary = {fake_open_instance: cameras_to_analyse}
        mock_json.load.side_effect = file_dictionary.get

        mock_process_images.run_model_on_images.return_value = {'Succeeded': 100}, [
            {'STATUS': 'Errored', 'Message': "sorry!"}]

        mock_open = MagicMock()
        with patch('builtins.open', mock_open):
            mock_open.return_value = fake_open_instance

            batch_process_images.main(command_line_args)

        mock_process_images.run_model_on_images.assert_called_once_with(
            start_date=yesterday,
            end_date=yesterday,
            json_key_path=json_key_path,
            model_blob_name='NewcastleV0_StaticObjectFilterV0',
            cameras_to_analyse=cameras_to_analyse,
            gcp_region=expected_gcp_region,
            gcp_project=expected_gcp_project
        )
