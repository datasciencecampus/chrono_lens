import pytest

from tests.chrono_lens.gcloud.filters import is_running_on_gcp, is_not_running_on_gcp

pytestmark = pytest.mark.skipif(is_not_running_on_gcp(), reason="Skipping as not running on GCP")

from unittest import TestCase
from unittest.mock import MagicMock

if is_running_on_gcp():
    import google.cloud.storage

from numpy.testing import assert_array_equal

from chrono_lens.gcloud.image_loader import load_image_from_blob, load_bgr_image_from_blob_as_rgb
from tests.chrono_lens.images.image_reader import read_test_image, read_test_image_as_raw_bytes


class TestFaultyImageDetector(TestCase):
    def test_load_greyscale_image_from_blob_with_valid_8bpp_image_returns_24bpp_image(self):
        image_file_name = 'Forced_Greyscale_TfL-images_20200620_2030_00001.01251.jpg'
        expected_image = read_test_image(image_file_name, 'failing_images')
        image_blob_name = 'test-blob'
        image_bucket = MagicMock()
        image_as_raw_bytes = read_test_image_as_raw_bytes(image_file_name, 'failing_images')
        mock_blob = MagicMock()
        image_bucket.blob.return_value = mock_blob
        mock_blob.download_as_string.return_value = image_as_raw_bytes

        actual_image = load_image_from_blob(image_blob_name, image_bucket)

        self.assertEqual(3, expected_image.shape[2], "failed to expand 8bpp image to 24bpp")
        assert_array_equal(expected_image, actual_image)

    def test_load_image_from_blob_with_valid_image_returns_image(self):
        image_file_name = 'TfL-images_20200620_2010_00001.01251.jpg'
        expected_image = read_test_image(image_file_name)
        image_blob_name = 'test-blob'
        image_bucket = MagicMock()
        image_as_raw_bytes = read_test_image_as_raw_bytes(image_file_name)
        mock_blob = MagicMock()
        image_bucket.blob.return_value = mock_blob
        mock_blob.download_as_string.return_value = image_as_raw_bytes

        actual_image = load_image_from_blob(image_blob_name, image_bucket)

        assert_array_equal(expected_image, actual_image)

    def test_load_image_from_blob_with_empty_file_returns_empty_array(self):
        image_blob_name = 'test-blob'
        image_bucket = MagicMock()
        mock_blob = MagicMock()
        image_bucket.blob.return_value = mock_blob
        mock_blob.download_as_string.return_value = b''

        actual_image = load_image_from_blob(image_blob_name, image_bucket)

        self.assertEqual(0, actual_image.shape[0])

    def test_load_image_from_blob_with_missing_file_returns_none(self):
        image_blob_name = 'test-blob'
        image_bucket = MagicMock()
        mock_blob = MagicMock()
        image_bucket.blob.return_value = mock_blob
        mock_blob.download_as_string.side_effect = google.api_core.exceptions.NotFound('')

        actual_image = load_image_from_blob(image_blob_name, image_bucket)

        self.assertIsNone(actual_image)

    def test_load_image_from_blob_with_corrupt_file_returns_empty_array(self):
        image_blob_name = 'test-blob'
        image_bucket = MagicMock()
        mock_blob = MagicMock()
        image_bucket.blob.return_value = mock_blob
        mock_blob.download_as_string.return_value = b'xgfhsthfgh'

        actual_image = load_image_from_blob(image_blob_name, image_bucket)

        self.assertEqual(0, actual_image.shape[0])

    def test_load_image_from_blob_as_rgb_with_valid_image_returns_image(self):
        image_file_name = 'TfL-images_20200620_2010_00001.01251.jpg'
        expected_image_bgr = read_test_image(image_file_name)
        expected_image_rgb = expected_image_bgr[..., ::-1]
        image_blob_name = 'test-blob'
        image_bucket = MagicMock()
        image_as_raw_bytes = read_test_image_as_raw_bytes(image_file_name)
        mock_blob = MagicMock()
        image_bucket.blob.return_value = mock_blob
        mock_blob.download_as_string.return_value = image_as_raw_bytes

        actual_image_rgb = load_bgr_image_from_blob_as_rgb(image_blob_name, image_bucket)

        assert_array_equal(expected_image_rgb, actual_image_rgb)

    def test_load_image_from_blob_as_rgb_with_missing_file_returns_none(self):
        image_blob_name = 'test-blob'
        mock_blob = MagicMock()
        mock_blob.download_as_string.side_effect = google.api_core.exceptions.NotFound('')
        image_bucket = MagicMock()
        image_bucket.blob.return_value = mock_blob

        actual_image = load_bgr_image_from_blob_as_rgb(image_blob_name, image_bucket)

        self.assertIsNone(actual_image)

    def test_load_image_from_blob_as_rgb_with_empty_file_returns_empty_array(self):
        image_blob_name = 'test-blob'
        image_bucket = MagicMock()
        mock_blob = MagicMock()
        image_bucket.blob.return_value = mock_blob
        mock_blob.download_as_string.return_value = b''

        actual_image = load_bgr_image_from_blob_as_rgb(image_blob_name, image_bucket)

        self.assertEqual(0, actual_image.shape[0])

    def test_load_image_from_blob_as_rgb_with_corrupted_file_returns_empty_array(self):
        image_blob_name = 'test-blob'
        image_bucket = MagicMock()
        mock_blob = MagicMock()
        image_bucket.blob.return_value = mock_blob
        mock_blob.download_as_string.return_value = b'dfgsdfgdgdfg'

        actual_image = load_bgr_image_from_blob_as_rgb(image_blob_name, image_bucket)

        self.assertEqual(0, actual_image.shape[0])
