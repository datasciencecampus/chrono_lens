import datetime
import unittest

import pytest
from mock import patch, MagicMock

from tests.chrono_lens.gcloud.filters import is_running_on_gcp, is_not_running_on_gcp

pytestmark = pytest.mark.skipif(is_not_running_on_gcp(), reason="Skipping as not running on GCP")

if is_running_on_gcp():
    from chrono_lens.gcloud import remove_images


class TestRemoveImages(unittest.TestCase):

    def setUp(self):
        self.expected_supplier_name = 'test'

        self.blob_20200101_1910 = MagicMock(name=f'{self.expected_supplier_name}/20200101/1910/image.jpg')
        self.blob_20200101_1920a = MagicMock(name=f'{self.expected_supplier_name}/20200101/1920/image.jpg')
        self.blob_20200101_1920b = MagicMock(name=f'{self.expected_supplier_name}/20200101/1920/image2.jpg')

        self.blob_20200102_0010 = MagicMock(name=f'{self.expected_supplier_name}/20200102/0010/test.jpg')

        self.blob_20200103_0740 = MagicMock(name=f'{self.expected_supplier_name}/20200103/0740/too-new.jpg')

        self.list_blobs = {
            f'{self.expected_supplier_name}/20200101/': [self.blob_20200101_1910, self.blob_20200101_1920a,
                                                         self.blob_20200101_1920b],
            f'{self.expected_supplier_name}/20200102/': [self.blob_20200102_0010],
            f'{self.expected_supplier_name}/20200103/': [self.blob_20200103_0740],
        }

    @patch('chrono_lens.gcloud.remove_images.page_iterator')
    @patch('chrono_lens.gcloud.remove_images.datetime')
    def test_deletes_only_old_blobs(self, mock_datetime, mock_page_iterator):
        maximum_number_of_days = 2
        data_bucket_name = 'dummyBucket'

        expected_number_of_cameras_per_sample = 4
        supplier_names_to_camera_counts = {self.expected_supplier_name: expected_number_of_cameras_per_sample}

        mock_storage_client = MagicMock()

        mock_datetime.date.today.return_value = datetime.date(2020, 1, 4)
        mock_datetime.datetime = datetime.datetime

        mock_page_iterator.HTTPIterator.return_value = list(self.list_blobs.keys())

        def fake_list_blobs(_bucket_name, prefix):
            return self.list_blobs[prefix]

        mock_storage_client.list_blobs = fake_list_blobs

        remove_images.remove_images_older_than_threshold(
            maximum_number_of_days, data_bucket_name, supplier_names_to_camera_counts, mock_storage_client
        )

        self.blob_20200101_1910.delete.assert_called_once()
        self.blob_20200101_1920a.delete.assert_called_once()
        self.blob_20200101_1920b.delete.assert_called_once()

        self.blob_20200102_0010.delete.assert_not_called()
        self.blob_20200103_0740.delete.assert_not_called()

    @patch('chrono_lens.gcloud.remove_images.page_iterator')
    @patch('chrono_lens.gcloud.remove_images.datetime')
    def test_deletes_only_old_blobs_extra_date_test(self, mock_datetime, mock_page_iterator):
        maximum_number_of_days = 1
        data_bucket_name = 'dummyBucket'

        expected_number_of_cameras_per_sample = 4
        supplier_names_to_camera_counts = {self.expected_supplier_name: expected_number_of_cameras_per_sample}

        mock_storage_client = MagicMock()

        mock_datetime.date.today.return_value = datetime.date(2020, 1, 4)
        mock_datetime.datetime = datetime.datetime

        mock_page_iterator.HTTPIterator.return_value = list(self.list_blobs.keys())

        def fake_list_blobs(_bucket_name, prefix):
            return self.list_blobs[prefix]

        mock_storage_client.list_blobs = fake_list_blobs

        remove_images.remove_images_older_than_threshold(
            maximum_number_of_days, data_bucket_name, supplier_names_to_camera_counts, mock_storage_client
        )

        self.blob_20200101_1910.delete.assert_called_once()
        self.blob_20200101_1920a.delete.assert_called_once()
        self.blob_20200101_1920b.delete.assert_called_once()
        self.blob_20200102_0010.delete.assert_called_once()

        self.blob_20200103_0740.delete.assert_not_called()

    @patch('chrono_lens.gcloud.remove_images.page_iterator')
    @patch('chrono_lens.gcloud.remove_images.datetime')
    def test_deletes_only_old_blobs_skips_non_date_folders(self, mock_datetime, mock_page_iterator):
        maximum_number_of_days = 1
        data_bucket_name = 'dummyBucket'

        extra_blobs = self.list_blobs.copy()
        blob_fish_bicycle = MagicMock(name=f'{self.expected_supplier_name}/fish/bicycle/too-new.jpg')
        extra_blobs[f'{self.expected_supplier_name}/fish/'] = [blob_fish_bicycle]

        expected_number_of_cameras_per_sample = 4
        supplier_names_to_camera_counts = {self.expected_supplier_name: expected_number_of_cameras_per_sample}

        mock_storage_client = MagicMock()

        mock_datetime.date.today.return_value = datetime.date(2020, 1, 4)
        mock_datetime.datetime = datetime.datetime

        mock_page_iterator.HTTPIterator.return_value = list(extra_blobs.keys())

        def fake_list_blobs(_bucket_name, prefix):
            return extra_blobs[prefix]

        mock_storage_client.list_blobs = fake_list_blobs

        remove_images.remove_images_older_than_threshold(
            maximum_number_of_days, data_bucket_name, supplier_names_to_camera_counts, mock_storage_client
        )

        self.blob_20200101_1910.delete.assert_called_once()
        self.blob_20200101_1920a.delete.assert_called_once()
        self.blob_20200101_1920b.delete.assert_called_once()
        self.blob_20200102_0010.delete.assert_called_once()

        self.blob_20200103_0740.delete.assert_not_called()
        blob_fish_bicycle.delete.assert_not_called()
