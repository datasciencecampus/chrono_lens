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

    @patch('chrono_lens.localhost.remove_images.datetime')
    def test_deletes_only_old_blobs_extra_date_test(self, mock_datetime):
        maximum_number_of_days = 1

        mock_datetime.date.today.return_value = datetime.date(2020, 1, 4)
        mock_datetime.datetime = datetime.datetime

        remove_images_older_than_threshold(
            maximum_number_of_days, self.download_folder_name
        )

        self.assertFalse(os.path.exists(f'{self.download_folder_name}/{self.supplier_name}/20200101/1910/image.jpg'))
        self.assertFalse(os.path.exists(f'{self.download_folder_name}/{self.supplier_name}/20200101/1920/image.jpg'))
        self.assertFalse(os.path.exists(f'{self.download_folder_name}/{self.supplier_name}/20200101/1920/image2.jpg'))
        self.assertFalse(os.path.exists(f'{self.download_folder_name}/{self.supplier_name}/20200102/0010/test.jpg'))

        self.assertTrue(os.path.exists(f'{self.download_folder_name}/{self.supplier_name}/20200103/0740/too-new.jpg'))
        self.assertTrue(os.path.exists(f'{self.download_folder_name}/other/stuff.txt'))

    @patch('chrono_lens.localhost.remove_images.datetime')
    def test_deletes_only_old_blobs_skips_non_date_folders(self, mock_datetime):
        maximum_number_of_days = 1

        self.fs.create_file(f'{self.download_folder_name}/other/gubbins/stuff.txt')

        mock_datetime.date.today.return_value = datetime.date(2020, 1, 4)
        mock_datetime.datetime = datetime.datetime

        remove_images_older_than_threshold(
            maximum_number_of_days, self.download_folder_name
        )

        self.assertFalse(os.path.exists(f'{self.download_folder_name}/{self.supplier_name}/20200101/1910/image.jpg'))
        self.assertFalse(os.path.exists(f'{self.download_folder_name}/{self.supplier_name}/20200101/1920/image.jpg'))
        self.assertFalse(os.path.exists(f'{self.download_folder_name}/{self.supplier_name}/20200101/1920/image2.jpg'))
        self.assertFalse(os.path.exists(f'{self.download_folder_name}/{self.supplier_name}/20200102/0010/test.jpg'))

        self.assertTrue(os.path.exists(f'{self.download_folder_name}/{self.supplier_name}/20200103/0740/too-new.jpg'))
        self.assertTrue(os.path.exists(f'{self.download_folder_name}/other/stuff.txt'))
        self.assertTrue(os.path.exists(f'{self.download_folder_name}/other/gubbins/stuff.txt'))
