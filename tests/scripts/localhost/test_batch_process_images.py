import datetime
import unittest

from mock import patch, ANY

from chrono_lens.exceptions import ProcessImagesException
from scripts.localhost import batch_process_images


class TestBatchProcessImages(unittest.TestCase):
    def test_start_date_incorrect_format(self):
        command_line_args = [
            '--start-date=fish',
            '--end-date=20200202'
        ]

        self.assertRaisesRegex(ProcessImagesException, 'Start date not in format "YYYYMMDD" or invalid date',
                               batch_process_images.main, command_line_args)

    def test_start_date_invalid(self):
        command_line_args = [
            '--start-date=20202020',
            '--end-date=202002202'
        ]

        self.assertRaisesRegex(ProcessImagesException, 'Start date not in format "YYYYMMDD" or invalid date',
                               batch_process_images.main, command_line_args)

    def test_start_date_invalid_too_short(self):
        command_line_args = [
            '--start-date=2020220',
            '--end-date=20200221'
        ]

        self.assertRaisesRegex(ProcessImagesException, 'Start date not in format "YYYYMMDD" or invalid date',
                               batch_process_images.main, command_line_args)

    def test_end_date_incorrect_format(self):
        command_line_args = [
            '--start-date=19991220',
            '--end-date=fishier'
        ]

        self.assertRaisesRegex(ProcessImagesException, 'End date not in format "YYYYMMDD" or invalid date',
                               batch_process_images.main, command_line_args)

    def test_end_date_invalid(self):
        command_line_args = [
            '--start-date=19911201',
            '--end-date=20200132'
        ]

        self.assertRaisesRegex(ProcessImagesException, 'End date not in format "YYYYMMDD" or invalid date',
                               batch_process_images.main, command_line_args)

    def test_end_date_invalid_too_short(self):
        command_line_args = [
            '--start-date=20201201',
            '--end-date=2020022'
        ]

        self.assertRaisesRegex(ProcessImagesException, 'End date not in format "YYYYMMDD" or invalid date',
                               batch_process_images.main, command_line_args)

    def test_start_date_after_end_date(self):
        command_line_args = [
            '--start-date=19911202',
            '--end-date=19911201'
        ]

        self.assertRaisesRegex(ProcessImagesException, 'Start date after end date',
                               batch_process_images.main, command_line_args)

    @patch('scripts.localhost.batch_process_images.batch_process')
    @patch('scripts.localhost.batch_process_images.date')
    @patch('scripts.localhost.batch_process_images.logging')
    def test_no_start_or_end_date_assumes_yesterday(self, _mock_logging, mock_date, mock_batch_process_images):
        today = datetime.date(year=2000, month=10, day=20)
        yesterday = datetime.date(year=2000, month=10, day=19)
        mock_date.today.return_value = today

        command_line_args = []

        batch_process_images.main(command_line_args)

        mock_batch_process_images.assert_called_once_with(
            config_path=ANY,
            download_path=ANY,
            counts_path=ANY,
            start_date=yesterday,
            end_date=yesterday
        )
