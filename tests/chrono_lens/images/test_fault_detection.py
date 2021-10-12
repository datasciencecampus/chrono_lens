from unittest import TestCase

from chrono_lens.images.fault_detection import FaultyImageDetector
from tests.chrono_lens.images.image_reader import read_test_image


class TestFaultyImageDetector(TestCase):

    def test_edge_case_current_is_not_faulty_and_previous_next_are_comparable(self):
        test_image_previous = read_test_image('TfL-images_20200620_2010_00001.01251.jpg')
        test_image_current = read_test_image('TfL-images_20200620_2020_00001.01251.jpg')
        test_image_next = read_test_image('TfL-images_20200620_2030_00001.01251.jpg')
        faulty_image_filter = FaultyImageDetector()
        previous_is_comparable, current_is_faulty, next_is_comparable = faulty_image_filter.check_current_faulty_and_next_previous_comparable(
            test_image_previous, test_image_current, test_image_next)

        self.assertTrue(previous_is_comparable)
        self.assertFalse(current_is_faulty)
        self.assertTrue(next_is_comparable)

    def test_mostly_current_grey_tarmac_image_is_not_faulty_and_previous_next_comparable(self):
        test_image_previous = read_test_image('NETravelData-images_20200508_1050_NT_A191E1.jpg')
        test_image_current = read_test_image('NETravelData-images_20200508_1100_NT_A191E1.jpg')
        test_image_next = read_test_image('NETravelData-images_20200508_1110_NT_A191E1.jpg')
        faulty_image_filter = FaultyImageDetector()

        previous_is_comparable, current_is_faulty, next_is_comparable = faulty_image_filter.check_current_faulty_and_next_previous_comparable(
            test_image_previous, test_image_current, test_image_next)

        self.assertTrue(previous_is_comparable)
        self.assertFalse(current_is_faulty)
        self.assertTrue(next_is_comparable)

    def test_mostly_current_grey_tarmac_image_alternate_is_not_faulty_and_previous_next_comparable(self):
        test_image_previous = read_test_image('NETravelData-images_20200508_1040_CM_A69A1-View_02.jpg')
        test_image_current = read_test_image('NETravelData-images_20200508_1050_CM_A69A1-View_02.jpg')
        test_image_next = read_test_image('NETravelData-images_20200508_1100_CM_A69A1-View_02.jpg')
        faulty_image_filter = FaultyImageDetector()

        previous_is_comparable, current_is_faulty, next_is_comparable = faulty_image_filter.check_current_faulty_and_next_previous_comparable(
            test_image_previous, test_image_current, test_image_next)

        self.assertTrue(previous_is_comparable)
        self.assertFalse(current_is_faulty)
        self.assertTrue(next_is_comparable)

    def test_example_is_not_faulty_image_next_previous_comparable(self):
        test_image_previous = read_test_image('TfL-images-20200501-0040-00001.08859.jpg')
        test_image_current = read_test_image('TfL-images-20200501-0050-00001.08859.jpg')
        test_image_next = read_test_image('TfL-images-20200501-0100-00001.08859.jpg')
        faulty_image_filter = FaultyImageDetector()

        previous_is_comparable, current_is_faulty, next_is_comparable = faulty_image_filter.check_current_faulty_and_next_previous_comparable(
            test_image_previous, test_image_current, test_image_next)

        self.assertTrue(previous_is_comparable)
        self.assertFalse(current_is_faulty)
        self.assertTrue(next_is_comparable)

    def test_present_current_next_but_missing_previous_flagged_as_not_comparable_not_faulty_comparable(self):
        test_image_previous = None
        test_image_current = read_test_image('TfL-images-20200501-0050-00001.08859.jpg')
        test_image_next = read_test_image('TfL-images-20200501-0100-00001.08859.jpg')
        faulty_image_filter = FaultyImageDetector()

        previous_is_comparable, current_is_faulty, next_is_comparable = faulty_image_filter.check_current_faulty_and_next_previous_comparable(
            test_image_previous, test_image_current, test_image_next)

        self.assertFalse(previous_is_comparable)
        self.assertFalse(current_is_faulty)
        self.assertTrue(next_is_comparable)

    def test_present_previous_current_missing_next_flagged_as_comparable_not_faulty_not_comparable(self):
        test_image_previous = read_test_image('TfL-images-20200501-0050-00001.08859.jpg')
        test_image_current = read_test_image('TfL-images-20200501-0100-00001.08859.jpg')
        test_image_next = None
        faulty_image_filter = FaultyImageDetector()

        previous_is_comparable, current_is_faulty, next_is_comparable = faulty_image_filter.check_current_faulty_and_next_previous_comparable(
            test_image_previous, test_image_current, test_image_next)

        self.assertTrue(previous_is_comparable)
        self.assertFalse(current_is_faulty)
        self.assertFalse(next_is_comparable)

    def test_previous_and_current_images_identical_flagged_as_not_comparable_faulty_comparable(self):
        test_image_previous = read_test_image('TfL-images-20200501-0040-00001.08859.jpg')
        test_image_current = read_test_image('TfL-images-20200501-0040-00001.08859.jpg')
        test_image_next = read_test_image('TfL-images-20200501-0050-00001.08859.jpg')
        faulty_image_filter = FaultyImageDetector()

        previous_is_comparable, current_is_faulty, next_is_comparable = faulty_image_filter.check_current_faulty_and_next_previous_comparable(
            test_image_previous, test_image_current, test_image_next)

        self.assertFalse(previous_is_comparable)
        self.assertTrue(current_is_faulty)
        self.assertTrue(next_is_comparable)

    def test_current_and_next_images_identical_flagged_as_comparable_not_faulty_not_comparable(self):
        test_image_previous = read_test_image('TfL-images-20200501-0040-00001.08859.jpg')
        test_image_current = read_test_image('TfL-images-20200501-0050-00001.08859.jpg')
        test_image_next = read_test_image('TfL-images-20200501-0050-00001.08859.jpg')

        faulty_image_filter = FaultyImageDetector()

        previous_is_comparable, current_is_faulty, next_is_comparable = faulty_image_filter.check_current_faulty_and_next_previous_comparable(
            test_image_previous, test_image_current, test_image_next)

        self.assertTrue(previous_is_comparable)
        self.assertFalse(current_is_faulty)
        self.assertFalse(next_is_comparable)

    def test_all_images_identical_flagged_not_comparable_faulty_not_comparable(self):
        test_image_previous = read_test_image('TfL-images-20200501-0040-00001.08859.jpg')
        test_image_current = read_test_image('TfL-images-20200501-0040-00001.08859.jpg')
        test_image_next = read_test_image('TfL-images-20200501-0040-00001.08859.jpg')

        faulty_image_filter = FaultyImageDetector()

        previous_is_comparable, current_is_faulty, next_is_comparable = faulty_image_filter.check_current_faulty_and_next_previous_comparable(
            test_image_previous, test_image_current, test_image_next)

        self.assertFalse(previous_is_comparable)
        self.assertTrue(current_is_faulty)
        self.assertFalse(next_is_comparable)

    def test_partial_current_image_with_stripes_current_flagged_as_faulty_previous_next_flagged_as_comparable(self):
        test_image_previous = read_test_image('TfL-images-20200501-0040-00001.08859.jpg')
        test_image_current = read_test_image('TfL-images_20200504_0240_00001.08859.jpg', 'failing_images')
        test_image_next = read_test_image('TfL-images_20200504_0250_00001.08859.jpg')
        faulty_image_filter = FaultyImageDetector()

        previous_is_comparable, current_is_faulty, next_is_comparable = faulty_image_filter.check_current_faulty_and_next_previous_comparable(
            test_image_previous, test_image_current, test_image_next)

        self.assertTrue(previous_is_comparable)
        self.assertTrue(current_is_faulty)
        self.assertTrue(next_is_comparable)

    def test_partial_current_image_with_stripes_flagged_missing_previous_flagged_as_not_comparable_faulty_comparable(
            self):
        test_image_previous = None
        test_image_current = read_test_image('TfL-images_20200504_0240_00001.08859.jpg', 'failing_images')
        test_image_next = read_test_image('TfL-images_20200501_0530_00001.08859.jpg')
        faulty_image_filter = FaultyImageDetector()

        previous_is_comparable, current_is_faulty, next_is_comparable = faulty_image_filter.check_current_faulty_and_next_previous_comparable(
            test_image_previous, test_image_current, test_image_next)

        self.assertFalse(previous_is_comparable)
        self.assertTrue(current_is_faulty)
        self.assertTrue(next_is_comparable)

    def test_paused_current_image_TfL_flagged_comparable_faulty_comparable(self):
        test_image_previous = read_test_image('TfL-images-20200501-0040-00001.08859.jpg')
        test_image_current = read_test_image('TfL-images_20200501_0520_00001.06592.jpg', 'failing_images')
        test_image_next = read_test_image('TfL-images_20200501_0530_00001.08859.jpg')
        faulty_image_filter = FaultyImageDetector()

        previous_is_comparable, current_is_faulty, next_is_comparable = faulty_image_filter.check_current_faulty_and_next_previous_comparable(
            test_image_previous, test_image_current, test_image_next)

        self.assertTrue(previous_is_comparable)
        self.assertTrue(current_is_faulty)
        self.assertTrue(next_is_comparable)

    def test_paused_current_image_TfL_missing_flagged_as_faulty_previous_flagged_as_not_comparable(self):
        test_image_previous = None
        test_image_current = read_test_image('TfL-images_20200501_0520_00001.06592.jpg', 'failing_images')
        test_image_next = read_test_image('TfL-images-20200501-0050-00001.08859.jpg')
        faulty_image_filter = FaultyImageDetector()

        previous_is_comparable, current_is_faulty, next_is_comparable = faulty_image_filter.check_current_faulty_and_next_previous_comparable(
            test_image_previous, test_image_current, test_image_next)

        self.assertFalse(previous_is_comparable)
        self.assertTrue(current_is_faulty)
        self.assertTrue(next_is_comparable)

    def test_paused_current_image_TfL_missing_flagged_as_faulty_next_flagged_as_not_comparable(self):
        test_image_previous = read_test_image('TfL-images-20200501-0050-00001.08859.jpg')
        test_image_current = read_test_image('TfL-images_20200501_0520_00001.06592.jpg', 'failing_images')
        test_image_next = None
        faulty_image_filter = FaultyImageDetector()

        previous_is_comparable, current_is_faulty, next_is_comparable = faulty_image_filter.check_current_faulty_and_next_previous_comparable(
            test_image_previous, test_image_current, test_image_next)

        self.assertTrue(previous_is_comparable)
        self.assertTrue(current_is_faulty)
        self.assertFalse(next_is_comparable)

    def test_paused_image_NETravelData_missing_previous_flagged_as_faulty_but_comparable(self):
        test_image_previous = read_test_image('NETravelData-images_20200508_1050_CM_A69A1-View_02.jpg')
        test_image_current = read_test_image('NETravelData-images_20200508_1800_NT_A193H1.jpg', 'failing_images')
        test_image_next = read_test_image('NETravelData-images_20200508_1100_CM_A69A1-View_02.jpg')
        faulty_image_filter = FaultyImageDetector()

        previous_is_comparable, current_is_faulty, next_is_comparable = faulty_image_filter.check_current_faulty_and_next_previous_comparable(
            test_image_previous, test_image_current, test_image_next)

        self.assertTrue(previous_is_comparable)
        self.assertTrue(current_is_faulty)
        self.assertTrue(next_is_comparable)

    def test_previous_and_current_are_different_dimensions_flagged_as_not_comparable_not_faulty_comparable(self):
        test_image_previous = read_test_image('NETravelData-images_20200508_1800_NT_A193H1.jpg', 'failing_images')
        test_image_current = read_test_image('TfL-images_20200502_0500_00001.06592.jpg')
        test_image_next = read_test_image('TfL-images_20200502_0510_00001.06592.jpg')
        faulty_image_filter = FaultyImageDetector()

        previous_is_comparable, current_is_faulty, next_is_comparable = faulty_image_filter.check_current_faulty_and_next_previous_comparable(
            test_image_previous, test_image_current, test_image_next)

        self.assertFalse(previous_is_comparable)
        self.assertFalse(current_is_faulty)
        self.assertTrue(next_is_comparable)

    def test_current_and_next_are_different_dimensions_flagged_as_comparable_not_faulty_not_comparable(self):
        test_image_previous = read_test_image('TfL-images_20200502_0500_00001.06592.jpg')
        test_image_current = read_test_image('TfL-images_20200502_0510_00001.06592.jpg')
        test_image_next = read_test_image('NETravelData-images_20200508_1800_NT_A193H1.jpg', 'failing_images')
        faulty_image_filter = FaultyImageDetector()

        previous_is_comparable, current_is_faulty, next_is_comparable = faulty_image_filter.check_current_faulty_and_next_previous_comparable(
            test_image_previous, test_image_current, test_image_next)

        self.assertTrue(previous_is_comparable)
        self.assertFalse(current_is_faulty)
        self.assertFalse(next_is_comparable)

    def test_all_have_same_dimensions_flagged_comparable_and_not_faulty(self):
        test_image_previous = read_test_image('TfL-images_20200502_0500_00001.06592.jpg')
        test_image_current = read_test_image('TfL-images_20200502_0510_00001.06592.jpg')
        test_image_next = read_test_image('TfL-images_20200502_0530_00001.06592.jpg')
        faulty_image_filter = FaultyImageDetector()

        previous_is_comparable, current_is_faulty, next_is_comparable = faulty_image_filter.check_current_faulty_and_next_previous_comparable(
            test_image_previous, test_image_current, test_image_next)

        self.assertTrue(previous_is_comparable)
        self.assertFalse(current_is_faulty)
        self.assertTrue(next_is_comparable)

    def test_next_and_current_same_dimensions_with_missing_previous_flagged_as_not_comparable_not_faulty_comparable(
            self):
        test_image_previous = None
        test_image_current = read_test_image('TfL-images_20200502_0510_00001.06592.jpg')
        test_image_next = read_test_image('TfL-images_20200502_0530_00001.06592.jpg')
        faulty_image_filter = FaultyImageDetector()

        previous_is_comparable, current_is_faulty, next_is_comparable = faulty_image_filter.check_current_faulty_and_next_previous_comparable(
            test_image_previous, test_image_current, test_image_next)

        self.assertFalse(previous_is_comparable)
        self.assertFalse(current_is_faulty)
        self.assertTrue(next_is_comparable)

    def test_current_and_previous_same_dimensions_with_missing_next_flagged_as_comparable_not_faulty_not_comparable(
            self):
        test_image_previous = read_test_image('TfL-images_20200502_0500_00001.06592.jpg')
        test_image_current = read_test_image('TfL-images_20200502_0510_00001.06592.jpg')
        test_image_next = None
        faulty_image_filter = FaultyImageDetector()

        previous_is_comparable, current_is_faulty, next_is_comparable = faulty_image_filter.check_current_faulty_and_next_previous_comparable(
            test_image_previous, test_image_current, test_image_next)

        self.assertTrue(previous_is_comparable)
        self.assertFalse(current_is_faulty)
        self.assertFalse(next_is_comparable)

    def test_missing_next_and_previous_not_comparable_current_not_faulty(self):
        test_image_previous = None
        test_image_current = read_test_image('TfL-images_20200502_0510_00001.06592.jpg')
        test_image_next = None
        faulty_image_filter = FaultyImageDetector()

        previous_is_comparable, current_is_faulty, next_is_comparable = faulty_image_filter.check_current_faulty_and_next_previous_comparable(
            test_image_previous, test_image_current, test_image_next)

        self.assertFalse(previous_is_comparable)
        self.assertFalse(current_is_faulty)
        self.assertFalse(next_is_comparable)

    def test_paused_previous_image_TfL_flagged_as_not_comparable_not_faulty_comparable(self):
        test_image_previous = read_test_image('TfL-images_20200501_0520_00001.06592.jpg', 'failing_images')
        test_image_current = read_test_image('TfL-images-20200501-0050-00001.08859.jpg')
        test_image_next = read_test_image('TfL-images-20200501-0100-00001.08859.jpg')
        faulty_image_filter = FaultyImageDetector()

        previous_is_comparable, current_is_faulty, next_is_comparable = faulty_image_filter.check_current_faulty_and_next_previous_comparable(
            test_image_previous, test_image_current, test_image_next)

        self.assertFalse(previous_is_comparable)
        self.assertFalse(current_is_faulty)
        self.assertTrue(next_is_comparable)

    def test_paused_next_image_TfL_flagged_as_comparable_not_faulty_not_comparable(self):
        test_image_previous = read_test_image('TfL-images-20200501-0050-00001.08859.jpg')
        test_image_current = read_test_image('TfL-images-20200501-0100-00001.08859.jpg')
        test_image_next = read_test_image('TfL-images_20200501_0520_00001.06592.jpg', 'failing_images')
        faulty_image_filter = FaultyImageDetector()

        previous_is_comparable, current_is_faulty, next_is_comparable = faulty_image_filter.check_current_faulty_and_next_previous_comparable(
            test_image_previous, test_image_current, test_image_next)

        self.assertTrue(previous_is_comparable)
        self.assertFalse(current_is_faulty)
        self.assertFalse(next_is_comparable)
