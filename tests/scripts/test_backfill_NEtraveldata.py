import datetime
import unittest
from os import environ

from mock import MagicMock, patch

from chrono_lens.exceptions import ProcessImagesException

PROJECT_ID = 'gcp_project'
with patch.dict(environ, {
    'PROJECT_ID': PROJECT_ID,
}):
    from scripts import backfill_NEtraveldata


class fake_open:
    def __init__(self):
        self.text = ""

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    def write(self, text):
        self.text += text


@patch('scripts.backfill_NEtraveldata.json')
class TestBackFillNETravelData(unittest.TestCase):
    default_json_files = {
        'cameras-to-analyse.json': {
            'test': ['a', 'b']
        },
        'ne-travel-sources.json': {}
    }

    def assert_backfill_raises_exception(self, expected_exception, expected_error_message, command_line_args,
                                         mock_json, json_files=None):

        if json_files is None:
            json_files = self.default_json_files

        open_side_effects = self.set_up_mock_json(json_files, mock_json)

        mock_open = MagicMock()
        with patch('builtins.open', mock_open):
            mock_open.side_effect = open_side_effects.get

            self.assertRaisesRegex(expected_exception, expected_error_message, backfill_NEtraveldata.main,
                                   command_line_args)

    @staticmethod
    def set_up_mock_json(json_files, mock_json):
        open_side_effects = {}
        load_side_effects = {}
        for json_filename in json_files:

            if type(json_files[json_filename]) is IOError:
                open_side_effects[json_filename] = json_files[json_filename]
            else:
                fake_open_instance = fake_open()

                load_side_effects[fake_open_instance] = json_files[json_filename]
                open_side_effects[json_filename] = fake_open_instance
        mock_json.load.side_effect = load_side_effects.get
        return open_side_effects

    def test_start_date_incorrect_format(self, mock_json):

        command_line_args = [
            '--JSON-private-key=somefile.json',
            '--start-date=fish',
            '--end-date=20200202',
            '--ne-travel-sources-json=ne-travel-sources.json',
            '--model-name=FaultyImageFilterV0_NewcastleV0_StaticObjectFilterV0'
        ]

        self.assert_backfill_raises_exception(ProcessImagesException,
                                              'Start date not in format "YYYYMMDD" or invalid date',
                                              command_line_args, mock_json)

    def test_start_date_invalid(self, mock_json):
        command_line_args = [
            '--JSON-private-key=somefile.json',
            '--start-date=20202020',
            '--end-date=202002202',
            '--ne-travel-sources-json=ne-travel-sources.json',
            '--model-name=FaultyImageFilterV0_NewcastleV0_StaticObjectFilterV0'
        ]

        self.assert_backfill_raises_exception(ProcessImagesException,
                                              'Start date not in format "YYYYMMDD" or invalid date',
                                              command_line_args, mock_json)

    def test_start_date_invalid_too_short(self, mock_json):
        command_line_args = [
            '--JSON-private-key=somefile.json',
            '--start-date=2020220',
            '--end-date=20200221',
            '--ne-travel-sources-json=ne-travel-sources.json',
            '--model-name=FaultyImageFilterV0_NewcastleV0_StaticObjectFilterV0'
        ]

        self.assert_backfill_raises_exception(ProcessImagesException,
                                              'Start date not in format "YYYYMMDD" or invalid date',
                                              command_line_args, mock_json)

    def test_end_date_incorrect_format(self, mock_json):
        command_line_args = [
            '--JSON-private-key=somefile.json',
            '--start-date=19991220',
            '--end-date=fishier',
            '--ne-travel-sources-json=ne-travel-sources.json',
            '--model-name=FaultyImageFilterV0_NewcastleV0_StaticObjectFilterV0'
        ]

        self.assert_backfill_raises_exception(ProcessImagesException,
                                              'End date not in format "YYYYMMDD" or invalid date',
                                              command_line_args, mock_json)

    def test_end_date_invalid(self, mock_json):
        command_line_args = [
            '--JSON-private-key=somefile.json',
            '--start-date=19911201',
            '--end-date=20200132',
            '--ne-travel-sources-json=ne-travel-sources.json',
            '--model-name=FaultyImageFilterV0_NewcastleV0_StaticObjectFilterV0'
        ]

        self.assert_backfill_raises_exception(ProcessImagesException,
                                              'End date not in format "YYYYMMDD" or invalid date',
                                              command_line_args, mock_json)

    def test_end_date_invalid_too_short(self, mock_json):
        command_line_args = [
            '--JSON-private-key=somefile.json',
            '--start-date=20201201',
            '--end-date=2020022',
            '--ne-travel-sources-json=ne-travel-sources.json',
            '--model-name=FaultyImageFilterV0_NewcastleV0_StaticObjectFilterV0'
        ]

        self.assert_backfill_raises_exception(ProcessImagesException,
                                              'End date not in format "YYYYMMDD" or invalid date',
                                              command_line_args, mock_json)

    def test_start_date_after_end_date(self, mock_json):
        command_line_args = [
            '--JSON-private-key=somefile.json',
            '--start-date=19911202',
            '--end-date=19911201',
            '--ne-travel-sources-json=ne-travel-sources.json',
            '--model-name=FaultyImageFilterV0_NewcastleV0_StaticObjectFilterV0'
        ]

        self.assert_backfill_raises_exception(ProcessImagesException,
                                              'Start date after end date',
                                              command_line_args, mock_json)

    def test_cannot_open_ne_travel_json_file(self, mock_json):
        ne_travel_json_file_name = 'testfile.json'
        command_line_args = [
            '--JSON-private-key=somefile.json',
            '--start-date=19911201',
            '--end-date=19911201',
            f'--ne-travel-sources-json={ne_travel_json_file_name}',
            '--model-name=FaultyImageFilterV0_NewcastleV0_StaticObjectFilterV0'
        ]

        json_files = {
            'cameras-to-analyse.json': {
                'test': ['a', 'b']
            },
            ne_travel_json_file_name: IOError("No such file"),
        }

        self.assert_backfill_raises_exception(ProcessImagesException,
                                              'Failed to read NE Travel Sources from JSON file '
                                              f'"{ne_travel_json_file_name}"',
                                              command_line_args, mock_json, json_files)

    @patch('scripts.backfill_NEtraveldata.upload_camera_images')
    @patch('scripts.backfill_NEtraveldata.remove_ne_travel_data_faulty_and_missing_entries')
    def test_all_args_correct(self, mock_remove_ne_travel_data_faulty_and_missing_entries,
                              mock_upload_camera_images, mock_json):
        command_line_args = [
            '--JSON-private-key=somefile.json',
            '--start-date=19911201',
            '--end-date=19911201',
            '--ne-travel-sources-json=ne-travel-sources.json',
            '--model-name=FaultyImageFilterV0_NewcastleV0_StaticObjectFilterV0'
        ]

        open_side_effects = self.set_up_mock_json(self.default_json_files, mock_json)

        mock_open = MagicMock()
        with patch('builtins.open', mock_open):
            mock_open.side_effect = open_side_effects.get

            backfill_NEtraveldata.main(command_line_args)

        mock_upload_camera_images.assert_called_once()

        mock_remove_ne_travel_data_faulty_and_missing_entries.assert_called_once()

    @patch('scripts.backfill_NEtraveldata.upload_camera_images')
    @patch('scripts.backfill_NEtraveldata.remove_ne_travel_data_faulty_and_missing_entries')
    @patch('scripts.backfill_NEtraveldata.date')
    def test_no_start_or_end_date_assumes_yesterday(self, mock_date,
                                                    mock_remove_ne_travel_data_faulty_and_missing_entries,
                                                    mock_upload_camera_images, mock_json):
        json_key_path = 'somefile.json'
        model_name = 'FaultyImageFilterV0_NewcastleV0_StaticObjectFilterV0'

        command_line_args = [
            f'--JSON-private-key={json_key_path}',
            '--ne-travel-sources-json=ne-travel-sources.json',
            f'--model-name={model_name}'
        ]

        today = datetime.date(year=2000, month=10, day=20)
        yesterday = datetime.datetime(year=2000, month=10, day=19)
        mock_date.today.return_value = today
        open_side_effects = self.set_up_mock_json(self.default_json_files, mock_json)

        mock_open = MagicMock()
        with patch('builtins.open', mock_open):
            mock_open.side_effect = open_side_effects.get

            backfill_NEtraveldata.main(command_line_args)

        mock_upload_camera_images.assert_called_once_with(
            self.default_json_files['ne-travel-sources.json'],
            yesterday,
            json_key_path=json_key_path,
            gcp_project=PROJECT_ID
        )

        mock_remove_ne_travel_data_faulty_and_missing_entries.assert_called_once_with(
            PROJECT_ID, model_name, json_key_path, yesterday
        )
