from unittest import TestCase

import cv2
import numpy as np

from chrono_lens.images.correction import resize_jpeg_image


class TestCorrection(TestCase):
    def test_none_supplied_returns_none(self):
        actual_bytes = resize_jpeg_image(None, 100)

        self.assertIsNone(actual_bytes)

    def test_empty_array_supplied_returns_none(self):
        actual_bytes = resize_jpeg_image([], 100)

        self.assertIsNone(actual_bytes)

    def test_garbage_array_supplied_returns_none(self):
        actual_bytes = resize_jpeg_image(b'not an image', 100)

        self.assertIsNone(actual_bytes)

    def test_small_image_supplied_returns_unchanged(self):
        image = np.ndarray(shape=(10, 10, 3))
        return_code, encoded_array = cv2.imencode('.jpg', image)
        encoded_bytes = encoded_array.tobytes()

        actual_bytes = resize_jpeg_image(encoded_bytes, 100)

        self.assertEqual(encoded_bytes, actual_bytes)

    def test_large_landscape_image_supplied_returns_downsized(self):
        image = np.ndarray(shape=(100, 50, 3))
        return_code, encoded_array = cv2.imencode('.jpg', image)
        encoded_bytes = encoded_array.tobytes()

        actual_bytes = resize_jpeg_image(encoded_bytes, 50)

        actual_image_bytes = np.asarray(bytearray(actual_bytes), dtype="uint8")
        actual_image = cv2.imdecode(actual_image_bytes, cv2.IMREAD_COLOR)
        self.assertEqual(actual_image.shape, (50, 25, 3))

    def test_large_portrait_image_supplied_returns_downsized(self):
        image = np.ndarray(shape=(40, 80, 3))
        return_code, encoded_array = cv2.imencode('.jpg', image)
        encoded_bytes = encoded_array.tobytes()

        actual_bytes = resize_jpeg_image(encoded_bytes, 60)

        actual_image_bytes = np.asarray(bytearray(actual_bytes), dtype="uint8")
        actual_image = cv2.imdecode(actual_image_bytes, cv2.IMREAD_COLOR)
        self.assertEqual(actual_image.shape, (30, 60, 3))
