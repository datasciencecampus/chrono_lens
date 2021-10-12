import os.path

import cv2


def read_test_image(filename, sub_folder_name='time_series', parent_folder='..'):
    common_folder_root = os.path.join(parent_folder, 'tests', 'test_data', sub_folder_name)
    image_filename = os.path.join(common_folder_root, filename)
    image = cv2.imread(image_filename)
    assert image is not None, f'Failed to load image "{filename}"'
    return image


def read_test_image_as_raw_bytes(filename, sub_folder_name='time_series', parent_folder='..'):
    common_folder_root = os.path.join(parent_folder, 'tests', 'test_data', sub_folder_name)
    image_filename = os.path.join(common_folder_root, filename)
    with open(image_filename, 'rb') as image_data:
        image = image_data.read()

    assert image is not None, f'Failed to load image "{filename}"'
    return image
