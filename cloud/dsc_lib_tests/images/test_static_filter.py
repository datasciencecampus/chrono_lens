from unittest import TestCase

from dsc_lib.images.static_filter import StaticObjectFilter
from dsc_lib_tests.images.image_reader import read_test_image

SCENECUT_THRESHOLD = 0.4
MINIMUM_MASK_PROPORTION = 0.25
MINIMUM_MASK_PROPORTION_PERSON = 0.10
CONFIDENCE_PERSON = 0.80
CONTOUR_AREA_THRESHOLD = 50


class TestStaticFilter(TestCase):

    def test_constructed_from_configuration(self):
        expected_scenecut_threshold = 1.23
        expected_minimum_mask_proportion = 2.34
        expected_minimum_mask_proportion_person = 3.45
        expected_confidence_person = 4.56
        expected_contour_areas_threshold = 5.67
        expected_ignore_comparable = False

        static_object_filter = StaticObjectFilter.from_configuration({
            'scenecut_threshold': expected_scenecut_threshold,
            'minimum_mask_proportion': expected_minimum_mask_proportion,
            'minimum_mask_proportion_person': expected_minimum_mask_proportion_person,
            'confidence_person': expected_confidence_person,
            'contour_area_threshold': expected_contour_areas_threshold
        })

        self.assertEqual(expected_scenecut_threshold, static_object_filter.scenecut_threshold)
        self.assertEqual(expected_minimum_mask_proportion, static_object_filter.minimum_mask_proportion)
        self.assertEqual(expected_minimum_mask_proportion_person, static_object_filter.minimum_mask_proportion_person)
        self.assertEqual(expected_confidence_person, static_object_filter.confidence_person)
        self.assertEqual(expected_contour_areas_threshold, static_object_filter.contour_area_threshold)

    def test_reject_static(self):
        previous_image_rgb = read_test_image('TfL-images-20200501-0040-00001.08859.jpg')
        current_image_rgb = read_test_image('TfL-images-20200501-0050-00001.08859.jpg')
        next_image_rgb = read_test_image('TfL-images-20200501-0100-00001.08859.jpg')

        detected_objects = [
            # [label name, [y0, x0, y1, x1, confidence]]
            ['van', [141, 241, 180, 285, 0.9964]],
            ['car', [127, 190, 145, 212, 0.9381]],
            ['van', [113, 169, 134, 188, 0.8928]],
            ['van', [125, 214, 154, 243, 0.8576]],
            ['person', [167, 105, 195, 114, 0.7773]],
            ['car', [123, 206, 141, 229, 0.5541]]
        ]

        expected_filtered_detected_objects = [
            # [label name, [y0, x0, y1, x1, confidence]]
            ['person', [167, 105, 195, 114, 0.7773]]
        ]

        static_object_filter = StaticObjectFilter(scenecut_threshold=SCENECUT_THRESHOLD,
                                                  minimum_mask_proportion=MINIMUM_MASK_PROPORTION,
                                                  minimum_mask_proportion_person=MINIMUM_MASK_PROPORTION_PERSON,
                                                  confidence_person=CONFIDENCE_PERSON,
                                                  contour_area_threshold=CONTOUR_AREA_THRESHOLD)
        filtered_detected_objects = static_object_filter.filter_static_objects(
            detected_objects, previous_image_rgb, current_image_rgb, next_image_rgb)

        self.assertListEqual(expected_filtered_detected_objects, filtered_detected_objects)

    def test_reject_small_static_if_person(self):
        previous_image_rgb = read_test_image('TfL-images-20200501-1320-00001.04542.jpg')
        current_image_rgb = read_test_image('TfL-images-20200501-1330-00001.04542.jpg')
        next_image_rgb = read_test_image('TfL-images-20200501-1340-00001.04542.jpg')

        detected_objects = [
            # [label name, [y0, x0, y1, x1, confidence]]
            ['car', [111, 164, 132, 190, 0.9994]],
            ['car', [128, 219, 163, 254, 0.9984]],
            ['car', [99, 184, 118, 206, 0.9954]],
            ['car', [91, 199, 109, 223, 0.9774]],
            ['car', [80, 139, 96, 172, 0.9738]],
            ['person', [122, 314, 151, 324, 0.9577]],
            ['person', [148, 28, 179, 38, 0.9366]],
            ['person', [117, 56, 142, 64, 0.9024]],
            ['car', [60, 258, 70, 268, 0.7689]],
            ['car', [77, 281, 93, 300, 0.7457]],
            ['car', [84, 219, 103, 255, 0.7399]]
        ]

        expected_filtered_detected_objects = [
            # [label name, [y0, x0, y1, x1, confidence]]
            ['car', [111, 164, 132, 190, 0.9994]],
            ['car', [128, 219, 163, 254, 0.9984]],
            ['car', [99, 184, 118, 206, 0.9954]],
            ['car', [91, 199, 109, 223, 0.9774]],
            ['car', [80, 139, 96, 172, 0.9738]],
            ['person', [122, 314, 151, 324, 0.9577]],
            ['person', [148, 28, 179, 38, 0.9366]],
            ['person', [117, 56, 142, 64, 0.9024]],
            ['car', [60, 258, 70, 268, 0.7689]],
            # ['car', [77, 281, 93, 300, 0.7457]],
            ['car', [84, 219, 103, 255, 0.7399]]
        ]

        static_object_filter = StaticObjectFilter(scenecut_threshold=SCENECUT_THRESHOLD,
                                                  minimum_mask_proportion=MINIMUM_MASK_PROPORTION,
                                                  minimum_mask_proportion_person=MINIMUM_MASK_PROPORTION_PERSON,
                                                  confidence_person=CONFIDENCE_PERSON,
                                                  contour_area_threshold=CONTOUR_AREA_THRESHOLD)
        filtered_detected_objects = static_object_filter.filter_static_objects(
            detected_objects, previous_image_rgb, current_image_rgb, next_image_rgb)

        self.assertListEqual(expected_filtered_detected_objects, filtered_detected_objects)

    # Scene discontinuity:
    #
    # 00001.08750 on 2020-05-01 at 14:40 to 00001.08750 on 2020-05-01 at 14:50
    # 00001.07550 on 2020-05-01 at 11:50 to 00001.07550 on 2020-05-01 at 12:00
    # 00001.07550 on 2020-05-01 at 13:20 to 00001.07550 on 2020-05-01 at 13:30
    #
    # 00001.06592 on 2020-05-01 at 05:40 to 00001.06592 on 2020-05-01 at 05:50
    # 00001.06592 on 2020-05-01 at 07:50 to 00001.06592 on 2020-05-01 at 08:00
    # 00001.06592 on 2020-05-01 at 08:00 to 00001.06592 on 2020-05-01 at 08:10
    # 00001.06592 on 2020-05-01 at 08:20 to 00001.06592 on 2020-05-01 at 08:30
    # 00001.06592 on 2020-05-01 at 08:40 to 00001.06592 on 2020-05-01 at 08:50
    # 00001.06592 on 2020-05-01 at 13:30 to 00001.06592 on 2020-05-01 at 13:40
    # 00001.06592 on 2020-05-01 at 15:00 to 00001.06592 on 2020-05-01 at 15:10
    #
    # 00001.04542 on 2020-05-01 at 12:30 to 00001.04542 on 2020-05-01 at 12:40
    # 00001.04542 on 2020-05-01 at 15:40 to 00001.04542 on 2020-05-01 at 15:50
    # 00001.04542 on 2020-05-01 at 16:00 to 00001.04542 on 2020-05-01 at 16:10
    # 00001.04542 on 2020-05-01 at 16:30 to 00001.04542 on 2020-05-01 at 16:40
    # 00001.04542 on 2020-05-01 at 17:10 to 00001.04542 on 2020-05-01 at 17:20
    #
    # 00001.03205 on 2020-05-01 at 07:20 to 00001.03205 on 2020-05-01 at 07:30
    # 00001.03205 on 2020-05-01 at 07:30 to 00001.03205 on 2020-05-01 at 07:40
    # 00001.03205 on 2020-05-01 at 07:50 to 00001.03205 on 2020-05-01 at 08:00
    # 00001.03205 on 2020-05-01 at 08:50 to 00001.03205 on 2020-05-01 at 09:00
    # 00001.03205 on 2020-05-01 at 11:00 to 00001.03205 on 2020-05-01 at 11:10
    # 00001.03205 on 2020-05-01 at 12:20 to 00001.03205 on 2020-05-01 at 12:30
    # 00001.03205 on 2020-05-01 at 12:30 to 00001.03205 on 2020-05-01 at 12:40
    # 00001.03205 on 2020-05-01 at 13:00 to 00001.03205 on 2020-05-01 at 13:10
    # 00001.03205 on 2020-05-01 at 14:50 to 00001.03205 on 2020-05-01 at 15:00
    # 00001.03205 on 2020-05-01 at 16:20 to 00001.03205 on 2020-05-01 at 16:30
    # 00001.03205 on 2020-05-01 at 16:30 to 00001.03205 on 2020-05-01 at 16:40
    # 00001.03205 on 2020-05-01 at 18:40 to 00001.03205 on 2020-05-01 at 18:50

    # prev_score < SCENECUT_THRESHOLD:
    #
    # 00001.08750 on 2020-05-01 at 14:50
    # 00001.07550 on 2020-05-01 at 12:00
    # 00001.07550 on 2020-05-01 at 13:30
    #
    # 00001.06592 on 2020-05-01 at 05:50
    # 00001.06592 on 2020-05-01 at 08:00
    # 00001.06592 on 2020-05-01 at 08:10
    # 00001.06592 on 2020-05-01 at 08:30
    # 00001.06592 on 2020-05-01 at 08:50
    # 00001.06592 on 2020-05-01 at 13:40
    # 00001.06592 on 2020-05-01 at 15:10
    #
    # 00001.04542 on 2020-05-01 at 12:40
    # 00001.04542 on 2020-05-01 at 15:50
    # 00001.04542 on 2020-05-01 at 16:10
    # 00001.04542 on 2020-05-01 at 16:40
    # 00001.04542 on 2020-05-01 at 17:20
    #
    # 00001.03205 on 2020-05-01 at 07:30
    # 00001.03205 on 2020-05-01 at 07:40
    # 00001.03205 on 2020-05-01 at 08:00
    # 00001.03205 on 2020-05-01 at 09:00
    # 00001.03205 on 2020-05-01 at 11:10
    # 00001.03205 on 2020-05-01 at 12:30
    # 00001.03205 on 2020-05-01 at 12:40
    # 00001.03205 on 2020-05-01 at 13:10
    # 00001.03205 on 2020-05-01 at 15:00
    # 00001.03205 on 2020-05-01 at 16:30
    # 00001.03205 on 2020-05-01 at 16:40
    # 00001.03205 on 2020-05-01 at 18:50

    def test_ignore_overlapping_bounding_boxes(self):
        # Instances:
        #
        # 00001.08859 on 2020-05-01 at 01:30
        # 00001.08859 on 2020-05-01 at 03:00
        # 00001.08859 on 2020-05-01 at 10:20
        # 00001.08859 on 2020-05-01 at 11:10
        # 00001.08859 on 2020-05-01 at 19:00
        # 00001.08859 on 2020-05-01 at 23:00
        # 00001.08859 on 2020-05-01 at 23:40
        # 00001.08859 on 2020-05-02 at 00:10
        # 00001.08859 on 2020-05-02 at 01:20
        #
        # 00001.08750 on 2020-05-01 at 02:20
        # 00001.08750 on 2020-05-01 at 04:30
        # 00001.08750 on 2020-05-01 at 09:00 **
        # 00001.08750 on 2020-05-01 at 13:40 **
        # 00001.08750 on 2020-05-01 at 14:40
        # 00001.08750 on 2020-05-01 at 15:40 **
        # 00001.08750 on 2020-05-01 at 16:40
        # 00001.08750 on 2020-05-01 at 18:20
        # 00001.08750 on 2020-05-01 at 19:40
        # 00001.08750 on 2020-05-01 at 23:00 **
        # 00001.08750 on 2020-05-01 at 23:50
        # 00001.08750 on 2020-05-02 at 00:20
        #
        # 00001.07550 on 2020-05-01 at 06:50
        # 00001.07550 on 2020-05-01 at 07:20
        # 00001.07550 on 2020-05-01 at 11:20
        # 00001.07550 on 2020-05-01 at 12:00 (no previous)
        # 00001.07550 on 2020-05-01 at 13:50
        # 00001.07550 on 2020-05-01 at 17:30
        #
        # 00001.06592 on 2020-05-01 at 02:50
        # 00001.06592 on 2020-05-01 at 07:00
        # 00001.06592 on 2020-05-01 at 08:30
        # 00001.06592 on 2020-05-01 at 10:40
        # 00001.06592 on 2020-05-01 at 11:00
        # 00001.06592 on 2020-05-01 at 12:50 **
        # 00001.06592 on 2020-05-01 at 14:20
        # 00001.06592 on 2020-05-01 at 15:40
        # 00001.06592 on 2020-05-01 at 15:50
        # 00001.06592 on 2020-05-01 at 17:40
        # 00001.06592 on 2020-05-01 at 22:20
        # 00001.06592 on 2020-05-02 at 01:40
        #
        # 00001.04542 on 2020-05-01 at 00:50
        # 00001.04542 on 2020-05-01 at 01:10
        # 00001.04542 on 2020-05-01 at 07:10
        # 00001.04542 on 2020-05-01 at 08:40
        # 00001.04542 on 2020-05-01 at 10:20
        # 00001.04542 on 2020-05-01 at 11:20
        # 00001.04542 on 2020-05-01 at 13:10
        # 00001.04542 on 2020-05-01 at 14:00
        # 00001.04542 on 2020-05-01 at 16:20
        # 00001.04542 on 2020-05-01 at 18:00
        # 00001.04542 on 2020-05-01 at 18:50
        #
        # 00001.03205 on 2020-05-01 at 10:30
        # 00001.03205 on 2020-05-01 at 11:10
        # 00001.03205 on 2020-05-01 at 11:50

        previous_image_rgb = read_test_image('TfL-images-20200501-1330-00001.08750.jpg')
        current_image_rgb = read_test_image('TfL-images-20200501-1340-00001.08750.jpg')
        next_image_rgb = read_test_image('TfL-images-20200501-1350-00001.08750.jpg')

        detected_objects = [
            # [label name, [y0, x0, y1, x1, confidence]]
            ['truck', [66, 160, 116, 213, 0.9992]],
            ['van', [163, 254, 211, 286, 0.9937]],
            ['car', [84, 90, 100, 117, 0.6885]],
            ['van', [183, 273, 288, 352, 0.6568]],
            ['car', [248, 207, 282, 245, 0.6485]],
            ['bus', [183, 272, 287, 349, 0.6367]],
            ['car', [120, 224, 159, 253, 0.6224]],
            ['van', [119, 224, 159, 254, 0.6201]],
            ['car', [52, 215, 64, 226, 0.5871]],
            ['car', [40, 210, 54, 223, 0.4548]],
            ['car', [48, 199, 62, 215, 0.4053]]
        ]

        expected_filtered_detected_objects = [
            # [label name, [y0, x0, y1, x1, confidence]]
            ['truck', [66, 160, 116, 213, 0.9992]],
            ['van', [163, 254, 211, 286, 0.9937]],
            ['car', [84, 90, 100, 117, 0.6885]],
            ['van', [183, 273, 288, 352, 0.6568]],
            ['car', [248, 207, 282, 245, 0.6485]],
            ['car', [120, 224, 159, 253, 0.6224]],
            ['car', [52, 215, 64, 226, 0.5871]],
            ['car', [40, 210, 54, 223, 0.4548]],
            ['car', [48, 199, 62, 215, 0.4053]]
        ]

        static_object_filter = StaticObjectFilter(scenecut_threshold=SCENECUT_THRESHOLD,
                                                  minimum_mask_proportion=MINIMUM_MASK_PROPORTION,
                                                  minimum_mask_proportion_person=MINIMUM_MASK_PROPORTION_PERSON,
                                                  confidence_person=CONFIDENCE_PERSON,
                                                  contour_area_threshold=CONTOUR_AREA_THRESHOLD)
        filtered_detected_objects = static_object_filter.filter_static_objects(
            detected_objects, previous_image_rgb, current_image_rgb, next_image_rgb)

        self.assertListEqual(expected_filtered_detected_objects, filtered_detected_objects)

    def test_accept_non_static_next_image_missing(self):
        previous_image_rgb = read_test_image('TfL-images-20200501-0040-00001.08859.jpg')
        current_image_rgb = read_test_image('TfL-images-20200501-0050-00001.08859.jpg')
        next_image_rgb = None

        detected_objects = [
            # [label name, [y0, x0, y1, x1, confidence]]
            ['van', [141, 241, 180, 285, 0.9964]],
            ['car', [127, 190, 145, 212, 0.9381]],
            ['van', [113, 169, 134, 188, 0.8928]],
            ['van', [125, 214, 154, 243, 0.8576]],
            ['person', [167, 105, 195, 114, 0.7773]],
            ['car', [123, 206, 141, 229, 0.5541]]
        ]

        # Copy of the above - with the filtered items commented out, as a reminder of what has been static filtered
        expected_filtered_detected_objects = [
            # [label name, [y0, x0, y1, x1, confidence]]
            # ['van', [141, 241, 180, 285, 0.9964]],
            # ['car', [127, 190, 145, 212, 0.9381]],
            # ['van', [113, 169, 134, 188, 0.8928]],
            # ['van', [125, 214, 154, 243, 0.8576]],
            ['person', [167, 105, 195, 114, 0.7773]],
            # ['car', [123, 206, 141, 229, 0.5541]]
        ]

        static_object_filter = StaticObjectFilter(scenecut_threshold=SCENECUT_THRESHOLD,
                                                  minimum_mask_proportion=MINIMUM_MASK_PROPORTION,
                                                  minimum_mask_proportion_person=MINIMUM_MASK_PROPORTION_PERSON,
                                                  confidence_person=CONFIDENCE_PERSON,
                                                  contour_area_threshold=CONTOUR_AREA_THRESHOLD)
        filtered_detected_objects = static_object_filter.filter_static_objects(
            detected_objects, previous_image_rgb, current_image_rgb, next_image_rgb)

        self.assertListEqual(expected_filtered_detected_objects, filtered_detected_objects)

    def test_accept_non_static_previous_image_missing(self):
        previous_image_rgb = None
        current_image_rgb = read_test_image('TfL-images-20200501-0050-00001.08859.jpg')
        next_image_rgb = read_test_image('TfL-images-20200501-0100-00001.08859.jpg')

        detected_objects = [
            # [label name, [y0, x0, y1, x1, confidence]]
            ['van', [141, 241, 180, 285, 0.9964]],
            ['car', [127, 190, 145, 212, 0.9381]],
            ['van', [113, 169, 134, 188, 0.8928]],
            ['van', [125, 214, 154, 243, 0.8576]],
            ['person', [167, 105, 195, 114, 0.7773]],
            ['car', [123, 206, 141, 229, 0.5541]]
        ]

        # Copy of the above - with the filtered items commented out, as a reminder of what has been static filtered
        expected_filtered_detected_objects = [
            # [label name, [y0, x0, y1, x1, confidence]]
            # ['van', [141, 241, 180, 285, 0.9964]],
            # ['car', [127, 190, 145, 212, 0.9381]],
            # ['van', [113, 169, 134, 188, 0.8928]],
            # ['van', [125, 214, 154, 243, 0.8576]],
            ['person', [167, 105, 195, 114, 0.7773]],
            # ['car', [123, 206, 141, 229, 0.5541]]
        ]

        static_object_filter = StaticObjectFilter(scenecut_threshold=SCENECUT_THRESHOLD,
                                                  minimum_mask_proportion=MINIMUM_MASK_PROPORTION,
                                                  minimum_mask_proportion_person=MINIMUM_MASK_PROPORTION_PERSON,
                                                  confidence_person=CONFIDENCE_PERSON,
                                                  contour_area_threshold=CONTOUR_AREA_THRESHOLD)
        filtered_detected_objects = static_object_filter.filter_static_objects(
            detected_objects, previous_image_rgb, current_image_rgb, next_image_rgb)

        self.assertListEqual(expected_filtered_detected_objects, filtered_detected_objects)

    def test_previous_is_None_and_next_and_current_identical_causes_current_faulty(
            self):
        previous_image_rgb = None
        current_image_rgb = read_test_image('TfL-images-20200501-0050-00001.08859.jpg')
        next_image_rgb = read_test_image('TfL-images-20200501-0050-00001.08859.jpg')

        detected_objects = [
            # [label name, [y0, x0, y1, x1, confidence]]
            ['van', [141, 241, 180, 285, 0.9964]],
            ['car', [127, 190, 145, 212, 0.9381]],
            ['van', [113, 169, 134, 188, 0.8928]],
            ['van', [125, 214, 154, 243, 0.8576]],
            ['person', [167, 105, 195, 114, 0.7773]],
            ['car', [123, 206, 141, 229, 0.5541]]
        ]

        static_object_filter = StaticObjectFilter(scenecut_threshold=SCENECUT_THRESHOLD,
                                                  minimum_mask_proportion=MINIMUM_MASK_PROPORTION,
                                                  minimum_mask_proportion_person=MINIMUM_MASK_PROPORTION_PERSON,
                                                  confidence_person=CONFIDENCE_PERSON,
                                                  contour_area_threshold=CONTOUR_AREA_THRESHOLD)
        filtered_detected_objects = static_object_filter.filter_static_objects(
            detected_objects, previous_image_rgb, current_image_rgb, next_image_rgb, True, False)

        self.assertIsNone(filtered_detected_objects)

    def test_not_ignore_comparable_and_previous_not_comparable_and_next_not_comparable_returns_faulty(self):
        previous_image_rgb = read_test_image('TfL-images-20200501-0050-00001.08859.jpg')
        current_image_rgb = read_test_image('TfL-images-20200501-0050-00001.08859.jpg')
        next_image_rgb = read_test_image('TfL-images-20200501-0050-00001.08859.jpg')

        detected_objects = [
            # [label name, [y0, x0, y1, x1, confidence]]
            ['van', [141, 241, 180, 285, 0.9964]],
            ['car', [127, 190, 145, 212, 0.9381]],
            ['van', [113, 169, 134, 188, 0.8928]],
            ['van', [125, 214, 154, 243, 0.8576]],
            ['person', [167, 105, 195, 114, 0.7773]],
            ['car', [123, 206, 141, 229, 0.5541]]
        ]

        static_object_filter = StaticObjectFilter(scenecut_threshold=SCENECUT_THRESHOLD,
                                                  minimum_mask_proportion=MINIMUM_MASK_PROPORTION,
                                                  minimum_mask_proportion_person=MINIMUM_MASK_PROPORTION_PERSON,
                                                  confidence_person=CONFIDENCE_PERSON,
                                                  contour_area_threshold=CONTOUR_AREA_THRESHOLD)
        filtered_detected_objects = static_object_filter.filter_static_objects(
            detected_objects, previous_image_rgb, current_image_rgb, next_image_rgb, False, False)

        self.assertIsNone(filtered_detected_objects)

    def test_next_and_current_identical_not_ignore_comparable_causes_next_ignored_then_flags_faulty(
            self):
        previous_image_rgb = None
        current_image_rgb = read_test_image('TfL-images-20200501-0050-00001.08859.jpg')
        next_image_rgb = read_test_image('TfL-images-20200501-0050-00001.08859.jpg')

        detected_objects = [
            # [label name, [y0, x0, y1, x1, confidence]]
            ['van', [141, 241, 180, 285, 0.9964]],
            ['car', [127, 190, 145, 212, 0.9381]],
            ['van', [113, 169, 134, 188, 0.8928]],
            ['van', [125, 214, 154, 243, 0.8576]],
            ['person', [167, 105, 195, 114, 0.7773]],
            ['car', [123, 206, 141, 229, 0.5541]]
        ]

        static_object_filter = StaticObjectFilter(scenecut_threshold=SCENECUT_THRESHOLD,
                                                  minimum_mask_proportion=MINIMUM_MASK_PROPORTION,
                                                  minimum_mask_proportion_person=MINIMUM_MASK_PROPORTION_PERSON,
                                                  confidence_person=CONFIDENCE_PERSON,
                                                  contour_area_threshold=CONTOUR_AREA_THRESHOLD)
        filtered_detected_objects = static_object_filter.filter_static_objects(
            detected_objects, previous_image_rgb, current_image_rgb, next_image_rgb, True, False)

        # previous is None and next is not comparable, so can't peform static filter - flag as faulty
        self.assertIsNone(filtered_detected_objects)
