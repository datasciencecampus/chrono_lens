import datetime
import os

from mock import patch
from pyfakefs.fake_filesystem_unittest import TestCase

from chrono_lens.localhost.remove_images import remove_images_older_than_threshold


class TestRemoveImages(TestCase):

    def setUp(self):
        self.setUpPyfakefs()

        self.download_folder_name = 'test'
        self.supplier_name = 'IMAGE_PROVIDER'

        self.fs.create_file(f'{self.download_folder_name}/{self.supplier_name}/20200101/1910/image.jpg')
        self.fs.create_file(f'{self.download_folder_name}/{self.supplier_name}/20200101/1920/image.jpg')
        self.fs.create_file(f'{self.download_folder_name}/{self.supplier_name}/20200101/1920/image2.jpg')

        self.fs.create_file(f'{self.download_folder_name}/{self.supplier_name}/20200102/0010/test.jpg')

        self.fs.create_file(f'{self.download_folder_name}/{self.supplier_name}/20200103/0740/too-new.jpg')

        self.fs.create_file(f'{self.download_folder_name}/other/stuff.txt')

    @patch('chrono_lens.localhost.remove_images.datetime')
    def test_deletes_only_old_blobs(self, mock_datetime):
        maximum_number_of_days = 2

        mock_datetime.date.today.return_value = datetime.date(2020, 1, 4)
        mock_datetime.datetime = datetime.datetime

        remove_images_older_than_threshold(
            maximum_number_of_days, self.download_folder_name
        )

        self.assertFalse(os.path.exists(f'{self.download_folder_name}/{self.supplier_name}/20200101/1910/image.jpg'))
        self.assertFalse(os.path.exists(f'{self.download_folder_name}/{self.supplier_name}/20200101/1920/image.jpg'))
        self.assertFalse(os.path.exists(f'{self.download_folder_name}/{self.supplier_name}/20200101/1920/image2.jpg'))

        self.assertTrue(os.path.exists(f'{self.download_folder_name}/{self.supplier_name}/20200102/0010/test.jpg'))
        self.assertTrue(os.path.exists(f'{self.download_folder_name}/{self.supplier_name}/20200103/0740/too-new.jpg'))
        self.assertTrue(os.path.exists(f'{self.download_folder_name}/other/stuff.txt'))

    # @patch('chrono_lens.gcloud.remove_images.page_iterator')
    # @patch('chrono_lens.gcloud.remove_images.datetime')
    # def test_deletes_only_old_blobs_extra_date_test(self, mock_datetime, mock_page_iterator):
    #     maximum_number_of_days = 1
    #     data_bucket_name = 'dummyBucket'
    #
    #     expected_number_of_cameras_per_sample = 4
    #     supplier_names_to_camera_counts = {self.expected_supplier_name: expected_number_of_cameras_per_sample}
    #
    #     mock_storage_client = MagicMock()
    #
    #     mock_datetime.date.today.return_value = datetime.date(2020, 1, 4)
    #     mock_datetime.datetime = datetime.datetime
    #
    #     mock_page_iterator.HTTPIterator.return_value = list(self.list_blobs.keys())
    #
    #     def fake_list_blobs(_bucket_name, prefix):
    #         return self.list_blobs[prefix]
    #
    #     mock_storage_client.list_blobs = fake_list_blobs
    #
    #     remove_images.remove_images_older_than_threshold(
    #         maximum_number_of_days, data_bucket_name, supplier_names_to_camera_counts, mock_storage_client
    #     )
    #
    #     self.blob_20200101_1910.delete.assert_called_once()
    #     self.blob_20200101_1920a.delete.assert_called_once()
    #     self.blob_20200101_1920b.delete.assert_called_once()
    #     self.blob_20200102_0010.delete.assert_called_once()
    #
    #     self.blob_20200103_0740.delete.assert_not_called()
    #
    # @patch('chrono_lens.gcloud.remove_images.page_iterator')
    # @patch('chrono_lens.gcloud.remove_images.datetime')
    # def test_deletes_only_old_blobs_skips_non_date_folders(self, mock_datetime, mock_page_iterator):
    #     maximum_number_of_days = 1
    #     data_bucket_name = 'dummyBucket'
    #
    #     extra_blobs = self.list_blobs.copy()
    #     blob_fish_bicycle = MagicMock(name=f'{self.expected_supplier_name}/fish/bicycle/too-new.jpg')
    #     extra_blobs[f'{self.expected_supplier_name}/fish/'] = [blob_fish_bicycle]
    #
    #     expected_number_of_cameras_per_sample = 4
    #     supplier_names_to_camera_counts = {self.expected_supplier_name: expected_number_of_cameras_per_sample}
    #
    #     mock_storage_client = MagicMock()
    #
    #     mock_datetime.date.today.return_value = datetime.date(2020, 1, 4)
    #     mock_datetime.datetime = datetime.datetime
    #
    #     mock_page_iterator.HTTPIterator.return_value = list(extra_blobs.keys())
    #
    #     def fake_list_blobs(_bucket_name, prefix):
    #         return extra_blobs[prefix]
    #
    #     mock_storage_client.list_blobs = fake_list_blobs
    #
    #     remove_images.remove_images_older_than_threshold(
    #         maximum_number_of_days, data_bucket_name, supplier_names_to_camera_counts, mock_storage_client
    #     )
    #
    #     self.blob_20200101_1910.delete.assert_called_once()
    #     self.blob_20200101_1920a.delete.assert_called_once()
    #     self.blob_20200101_1920b.delete.assert_called_once()
    #     self.blob_20200102_0010.delete.assert_called_once()
    #
    #     self.blob_20200103_0740.delete.assert_not_called()
    #     blob_fish_bicycle.delete.assert_not_called()
