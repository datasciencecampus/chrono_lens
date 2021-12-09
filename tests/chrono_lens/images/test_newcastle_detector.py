import os
from unittest import TestCase

import cv2

from chrono_lens.images.newcastle_detector import NewcastleDetector


class TestNewcastleDetector(TestCase):
    @classmethod
    def setUpClass(cls):
        small_sample_image_filename = 'TfL_20200315_1300_00001.01251.jpg'
        sample_image_path = os.path.join('tests', 'test_data', 'test_detector_data',
                                         small_sample_image_filename)
        raw_small_sample_image_bgr = cv2.imread(sample_image_path)
        cls.raw_small_sample_image_rgb = cv2.cvtColor(raw_small_sample_image_bgr.copy(), cv2.COLOR_BGR2RGB)

        large_sample_image_filename = 'NETravelData-images_20200508_1110_NT_A191E1.jpg'
        raw_large_sample_image_bgr = cv2.imread(os.path.join('tests', 'test_data', 'time_series',
                                                             large_sample_image_filename))
        cls.raw_large_sample_image_rgb = cv2.cvtColor(raw_large_sample_image_bgr.copy(), cv2.COLOR_BGR2RGB)

        rcnn_serialised_model_filename = 'fig_frcnn_rebuscov-3.pb'
        with open(os.path.join('tests', 'test_data', 'test_detector_data',
                               rcnn_serialised_model_filename), 'rb') as fp:
            cls.rcnn_serialised_model = fp.read()

    def test_identifies_items_in_small_image(self):

        object_detector = NewcastleDetector(serialized_graph=self.rcnn_serialised_model, minimum_confidence=0.33)

        object_counts = {object_type: 0 for object_type in object_detector.detected_object_types()}

        detected_objects = object_detector.detect(self.raw_small_sample_image_rgb)

        for detected_object in detected_objects:
            label = detected_object[0].lower().strip()
            object_counts[label] += 1

        self.assertTrue('person' in object_counts)
        self.assertEqual(4, object_counts['person'])  # low count, looks more like ~10 but very occluded
        self.assertTrue('car' in object_counts)
        self.assertEqual(9, object_counts['car'])  # possibly 11 cars, very blurry and pixelated
        self.assertTrue('truck' in object_counts)
        self.assertEqual(1, object_counts['truck'])  # possibly a truck near the bus, or construction material
        self.assertTrue('bus' in object_counts)
        self.assertEqual(1, object_counts['bus'])  # correct
        self.assertTrue('cyclist' in object_counts)
        self.assertEqual(0, object_counts['cyclist'])  # correct
        self.assertTrue('motorcyclist' in object_counts)
        self.assertEqual(0, object_counts['motorcyclist'])  # correct
        self.assertTrue('van' in object_counts)
        self.assertEqual(0, object_counts['van'])  # correct

    def test_identifies_objects_in_different_size_images(self):

        object_detector = NewcastleDetector(serialized_graph=self.rcnn_serialised_model, minimum_confidence=0.33)

        detected_objects = object_detector.detect(self.raw_small_sample_image_rgb)

        object_counts = {object_type: 0 for object_type in object_detector.detected_object_types()}
        for detected_object in detected_objects:
            label = detected_object[0].lower().strip()
            object_counts[label] += 1

        self.assertTrue('person' in object_counts)
        self.assertEqual(4, object_counts['person'])  # low count, looks more like ~10 but very occluded
        self.assertTrue('car' in object_counts)
        self.assertEqual(9, object_counts['car'])  # possibly 11 cars, very blurry and pixelated
        self.assertTrue('truck' in object_counts)
        self.assertEqual(1, object_counts['truck'])  # possibly a truck near the bus, or construction material
        self.assertTrue('bus' in object_counts)
        self.assertEqual(1, object_counts['bus'])  # correct
        self.assertTrue('cyclist' in object_counts)
        self.assertEqual(0, object_counts['cyclist'])  # correct
        self.assertTrue('motorcyclist' in object_counts)
        self.assertEqual(0, object_counts['motorcyclist'])  # correct
        self.assertTrue('van' in object_counts)
        self.assertEqual(0, object_counts['van'])  # correct

        detected_objects = object_detector.detect(self.raw_large_sample_image_rgb)

        object_counts = {object_type: 0 for object_type in object_detector.detected_object_types()}
        for detected_object in detected_objects:
            label = detected_object[0].lower().strip()
            object_counts[label] += 1

        self.assertTrue('person' in object_counts)
        self.assertEqual(1, object_counts['person'])  # low count, can see 4 cyclists, but v. poor quality
        self.assertTrue('car' in object_counts)
        self.assertEqual(5, object_counts['car'])  # correct
        self.assertTrue('truck' in object_counts)
        self.assertEqual(0, object_counts['truck'])  # correct
        self.assertTrue('bus' in object_counts)
        self.assertEqual(0, object_counts['bus'])  # correct
        self.assertTrue('cyclist' in object_counts)
        self.assertEqual(0, object_counts['cyclist'])  # can see 4 cyclists, but v. poor quality image
        self.assertTrue('motorcyclist' in object_counts)
        self.assertEqual(0, object_counts['motorcyclist'])  # correct
        self.assertTrue('van' in object_counts)
        self.assertEqual(0, object_counts['van'])  # correct
