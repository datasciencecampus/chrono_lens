import unittest
from os import environ
from unittest.mock import ANY

from mock import patch

PROJECT_ID = 'gcp_project'
with patch.dict(environ, {
    'PROJECT_ID': PROJECT_ID,
}):
    from scripts import remove_old_images


class TestRemoveOldImages(unittest.TestCase):
    def test_max_image_age_out_of_range(self):
        command_line_args = [
            '--JSON-private-key=somefile.json',
            '--maximum-number-of-days=0',
        ]

        self.assertRaisesRegex(ValueError, '--maximum-number-of-days must be 1 or higher',
                               remove_old_images.main, command_line_args)

    @patch("scripts.remove_old_images.storage")
    @patch("scripts.remove_old_images.remove_images_older_than_threshold")
    def test_all_params_ok_assumes_NETravelData(self, mock_remove_images_older_than_threshold, _mock_storage):
        command_line_args = [
            '--JSON-private-key=somefile.json',
            '--maximum-number-of-days=1',
        ]

        remove_old_images.main(command_line_args)

        # No files mocked, so nothing to add - except assumed NETravelData
        mock_remove_images_older_than_threshold.assert_called_once_with(
            1, 'data-gcp_project', {'NETravelData-images': 350}, ANY)
