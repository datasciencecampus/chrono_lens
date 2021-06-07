import numpy as np


class FaultyImageDetector:
    @classmethod
    def from_configuration(cls, configuration):
        return cls(
            identical_area_proportion_threshold=configuration['identical_area_proportion_threshold'],
            row_similarity_threshold=configuration['row_similarity_threshold'],
            consecutive_matching_rows_threshold=configuration['consecutive_matching_rows_threshold']
        )

    def __init__(self, identical_area_proportion_threshold=0.33, row_similarity_threshold=0.8,
                 consecutive_matching_rows_threshold=0.2):
        """
        :param identical_area_proportion_threshold: percentage of image detected as a pure grey (R=G=B), for an image
        to be considered faulty

        :param row_similarity_threshold: percentage of pixels to match between rows
        (i.e. if row1[x] == row2[x] for more than the defined percentage x, we consider the row a match)

        :param consecutive_matching_rows_threshold: percentage of height that must have consecutive matching rows
        (taking into account #row_similarity_threshold) for an image to be considered as faulty
        """
        self.identical_area_proportion_threshold = identical_area_proportion_threshold
        self.row_similarity_threshold = row_similarity_threshold
        self.consecutive_matching_rows_threshold = consecutive_matching_rows_threshold

    def check_current_faulty_and_next_previous_comparable(self, previous_rgb_image, current_rgb_image, next_rgb_image):
        """
        Examines supplied images and determines if they can be used for further processing.

        :param previous_rgb_image: previous image as RGB numpy array or None
        :param current_rgb_image: current image as RGB numpy array; assumed not None
        :param next_rgb_image: next image as RGB numpy array or None
        :return: tuple of 3 booleans:
            if previous image is valid and could be used for comparison,
            if current image is valid and can be used for object detection,
            if next image is valid and could be used for comparison
        """
        previous_comparable = previous_rgb_image is not None
        current_faulty = False
        next_comparable = next_rgb_image is not None

        if previous_comparable:
            if previous_rgb_image.shape != current_rgb_image.shape:
                previous_comparable = False

            elif self.are_images_identical(previous_rgb_image, current_rgb_image):
                previous_comparable = False
                current_faulty = True

        if next_comparable:
            if current_rgb_image.shape != next_rgb_image.shape:
                next_comparable = False

            elif self.are_images_identical(current_rgb_image, next_rgb_image):
                next_comparable = False

        if self.largest_proportion_of_a_single_colour(current_rgb_image) > self.identical_area_proportion_threshold:
            current_faulty = True

        if previous_comparable:
            if self.largest_proportion_of_a_single_colour(
                    previous_rgb_image) > self.identical_area_proportion_threshold:
                previous_comparable = False

        if next_comparable:
            if self.largest_proportion_of_a_single_colour(next_rgb_image) > self.identical_area_proportion_threshold:
                next_comparable = False

        if self.maximum_number_of_consecutive_matching_rows(
                current_rgb_image) > current_rgb_image.shape[0] * self.consecutive_matching_rows_threshold:
            current_faulty = True

        if previous_comparable:
            if self.maximum_number_of_consecutive_matching_rows(
                    previous_rgb_image) > previous_rgb_image.shape[0] * self.consecutive_matching_rows_threshold:
                previous_comparable = False

        if next_comparable:
            if self.maximum_number_of_consecutive_matching_rows(
                    next_rgb_image) > next_rgb_image.shape[0] * self.consecutive_matching_rows_threshold:
                next_comparable = False

        return previous_comparable, current_faulty, next_comparable

    def maximum_number_of_consecutive_matching_rows(self, current_rgb_image):

        def rows_match(row1, row2):
            row_diff = row1 - row2
            number_of_same_component = np.sum(row_diff == 0)
            return number_of_same_component > row1.shape[0] * 3 * self.row_similarity_threshold

        max_consecutive_row_match_count = 0
        current_row_match_count = 0
        for y in range(current_rgb_image.shape[0] - 1):
            if rows_match(current_rgb_image[y], current_rgb_image[y + 1]):
                current_row_match_count += 1
            else:
                if current_row_match_count > max_consecutive_row_match_count:
                    max_consecutive_row_match_count = current_row_match_count
                current_row_match_count = 0
        if current_row_match_count > max_consecutive_row_match_count:
            max_consecutive_row_match_count = current_row_match_count

        return max_consecutive_row_match_count

    @staticmethod
    def largest_proportion_of_a_single_colour(img):
        quantised_range = 32
        quantised_fraction = 256 / quantised_range

        quantised_colours = np.zeros((quantised_range, quantised_range, quantised_range))
        # Sparse sampling will be sufficient - we're sampling every 4th pixel in X & Y,
        # so 1/16 sampled - to balance this, each count is +16 rather than +1
        for y in range(0, img.shape[0], 4):
            for x in range(0, img.shape[1], 4):
                r, g, b = img[y, x, :]
                quantised_r = int(r / quantised_fraction)
                quantised_g = int(r / quantised_fraction)
                quantised_b = int(r / quantised_fraction)
                quantised_colours[quantised_r, quantised_g, quantised_b] += 16

        highest_quantised_count = np.amax(quantised_colours)
        largest_proportion = highest_quantised_count / (img.shape[0] * img.shape[1])

        return largest_proportion

    @staticmethod
    def are_images_identical(image_0, image_1):
        return not (np.bitwise_xor(image_0, image_1).any())
