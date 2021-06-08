import cv2
import numpy as np
from skimage.metrics import structural_similarity

"""
Example JSON configuration:
{
    "scenecut_threshold": 0.4,
    "minimum_mask_area": 0.25,
    "minimum_mask_area_person": 0.10,
    "confidence_person": 0.80,
    "contour_area_threshold": 50
}
"""


class StaticObjectFilter:

    @classmethod
    def from_configuration(cls, configuration):
        return cls(
            scenecut_threshold=configuration['scenecut_threshold'],
            minimum_mask_proportion=configuration['minimum_mask_proportion'],
            minimum_mask_proportion_person=configuration['minimum_mask_proportion_person'],
            confidence_person=configuration['confidence_person'],
            contour_area_threshold=configuration['contour_area_threshold']
        )

    def __init__(self, scenecut_threshold=0.4, minimum_mask_proportion=0.25, minimum_mask_proportion_person=0.10,
                 confidence_person=0.80, contour_area_threshold=50):

        # the ssim value is between [0,1], the higher, the more similar to the previous image.
        self.scenecut_threshold = scenecut_threshold

        # if a mask has a smaller proportion of masked pixels than this, it is ignored
        self.minimum_mask_proportion = minimum_mask_proportion

        # Person's bounding box is smaller than vehicles but can be unreliable, so only use if higher confidence
        # otherwise minimum_mask_area is used
        self.minimum_mask_proportion_person = minimum_mask_proportion_person
        self.confidence_person = confidence_person

        # ANY CONTOUR SMALLER THAN THIS VALUE will be treated as noise.
        self.contour_area_threshold = contour_area_threshold

    def filter_static_objects(self, detected_objects, previous_image_rgb, current_image_rgb, next_image_rgb,
                              previous_comparable=True, next_comparable=True):
        """
        Given a list of detected objects (bounding box, label), compares against next and previous image;
        only checks against next/previous images if related "comparable" parameter is true.

        If the current image is deemed faulty as a result of these checks, we return None; otherwise we return a
        list of detected objects (equal to or a subset of the supplied detected_objects).

        Current image is deemed "faulty" if we cannot apply a static filter to it; this is skipped if
        "self.ignore_comparable" is True.

        :param detected_objects: list of labelled bounding boxes representing detected objects
        :param previous_image_rgb: numpy array of previous image in sequence, possibly None
        :param current_image_rgb: numpy array of current image in sequence
        :param next_image_rgb: numpy array of next image in sequence, possibly None
        :param previous_comparable: True if previous image is valid for comparison (and should be used), False otherwise
        :param next_comparable: True if previous image is valid for comparison (and should be used), False otherwise
        :return: list of labelled bounding boxes, a copy of `detected_objects` with static objects removed; None if
                 current_image is detected as faulty and code cannot apply a static filter
        """
        # early exit if we haven't been supplied with a list -
        if detected_objects is None:
            return None

        # Remove duplicate labels (where area of detected object significantly overlaps)
        detected_objects_no_duplicates = self._remove_duplicated_labels(detected_objects)

        # Need to filter for incomparable image sizes
        if not previous_comparable:
            previous_image_rgb = None

        if not next_comparable:
            next_image_rgb = None

        # If we can't compare against both previous and next, we can't perform a static object test
        # So assume 0 counts and flag faulty, we'll defer to imputation - to avoid unusually high counts
        if previous_image_rgb is None and next_image_rgb is None:
            return None

        current_image_greyscale = cv2.cvtColor(current_image_rgb, cv2.COLOR_BGR2GRAY)

        # Generate previous filename, get previous image
        if previous_image_rgb is None:
            previous_image_ssim_score = 0
            previous_image_ssim_full_image = None
        else:
            previous_image_greyscale = cv2.cvtColor(previous_image_rgb, cv2.COLOR_BGR2GRAY)
            (previous_image_ssim_score, previous_image_ssim_full_image) = structural_similarity(
                previous_image_greyscale, current_image_greyscale, full=True)

        if next_image_rgb is None:
            # if no next image, use mask = get_static_mask(previous_mask)
            # previous_image_rgb cannot be None, already checked
            mask = self._get_static_mask(previous_image_ssim_full_image)
        else:
            next_image_greyscale = cv2.cvtColor(next_image_rgb, cv2.COLOR_BGR2GRAY)
            (next_image_ssim_score, next_image_ssim_full_image) = structural_similarity(
                next_image_greyscale, current_image_greyscale, full=True)

            # if previous score and next score > SCENECUT:
            if (previous_image_rgb is not None) and (previous_image_ssim_score > self.scenecut_threshold) and (
                    next_image_ssim_score > self.scenecut_threshold):
                #   create previous mask
                #   create next mask
                previous_mask = self._get_static_mask(previous_image_ssim_full_image)
                next_mask = self._get_static_mask(next_image_ssim_full_image)

                #   mask = previous mask and next mask
                mask = cv2.bitwise_and(previous_mask, next_mask)

            else:
                #   mask = create next mask
                mask = self._get_static_mask(next_image_ssim_full_image)

        filtered_detected_objects = []

        # Extract bounding boxes for each result
        for detected_object in detected_objects_no_duplicates:
            #   If proportion of non-zero mask pixels within bounding box > minimum_mask_area
            #   OR label=="person" & score > confidence_person & proportion of ... > minimum_mask_area_person
            #     filtered_detected_objects.append(object)
            # ['van', [141, 241, 180, 285, 0.9964]],
            label = detected_object[0]
            y0, x0, y1, x1, score = detected_object[1]
            num_non_masked_pixels = np.sum(mask[y0:y1, x0:x1] > 0)
            proportion_masked_pixels = num_non_masked_pixels / ((y1 - y0 + 1) * (x1 - x0 + 1))

            if proportion_masked_pixels >= self.minimum_mask_proportion or (
                    label.find('person') >= 0 and
                    proportion_masked_pixels >= self.minimum_mask_proportion_person and
                    score > self.confidence_person):
                filtered_detected_objects.append(detected_object)

        return filtered_detected_objects

    def _get_static_mask(self, structural_similarity_image):
        # check SSIM, note ssimimg value is between [0,1] where the higher, the more similar
        structural_similarity_image = (structural_similarity_image * 255).astype("uint8")
        structural_similarity_image = 255 - structural_similarity_image

        # ret,structural_similarity_binary = cv2.threshold(ssimimg,127,255,cv2.THRESH_BINARY)
        ret, structural_similarity_binary = cv2.threshold(structural_similarity_image, 110, 255, cv2.THRESH_BINARY)

        # morphological operation to remove small noise and fill holes
        kernel = np.ones((3, 3), np.uint8)
        structural_similarity_binary = cv2.dilate(structural_similarity_binary, kernel=kernel)
        structural_similarity_binary = cv2.erode(structural_similarity_binary, kernel=kernel)

        # use contour to filter out small noise area
        contours, hierarchy = cv2.findContours(structural_similarity_binary, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        if len(contours) > 0:
            hierarchy = hierarchy[0]  # get the actual inner list of hierarchy descriptions

            # For each contour, filter small area
            for component in zip(contours, hierarchy):
                current_contour = component[0]
                current_hierarchy = component[1]
                if current_hierarchy[3] < 0:  # outer contour
                    area_contour = cv2.contourArea(current_contour)
                    if area_contour < self.contour_area_threshold:
                        cv2.drawContours(structural_similarity_binary, [current_contour], 0, color=0,
                                         thickness=cv2.FILLED)

        # fill small hole again
        structural_similarity_binary = cv2.dilate(structural_similarity_binary, kernel=kernel)
        structural_similarity_binary = cv2.erode(structural_similarity_binary, kernel=kernel)

        return structural_similarity_binary

    def _remove_duplicated_labels(self, detected_objects, maxratio=0.90):
        for index, object_ in enumerate(detected_objects):
            # label = object_[0]
            y0, x0, y1, x1, score = object_[1]
            source_bbox = (x0, y0, x1, y1)

            total_objects = len(detected_objects)
            test_index = index + 1
            while test_index < total_objects:
                # templabel = img_objects[tempindex][0]
                test_y0, test_x0, test_y1, test_x1, test_score = detected_objects[test_index][1]
                test_bbox = (test_x0, test_y0, test_x1, test_y1)
                ratio = self._calculate_intersection_over_union(source_bbox, test_bbox)

                # print(ratio)
                if ratio > maxratio:
                    # print(ratio)
                    if score > test_score:
                        # remove
                        # print(f'duplicated: keep {object_}  remove {detected_objects[tempindex]}')
                        detected_objects.pop(test_index)
                    else:
                        # print(f'duplicated: keep {detected_objects[tempindex]}  remove {object_}')
                        detected_objects.pop(index)
                    total_objects -= 1
                test_index += 1

        return detected_objects

    @staticmethod
    def _calculate_intersection_over_union(bbox1, bbox2):
        intersect_bbox = []
        if bbox2[0] >= bbox1[2] or bbox2[2] <= bbox1[0] or bbox2[1] >= bbox1[3] or bbox2[3] <= bbox1[1]:
            return 0
        else:
            intersect_bbox.append([max(bbox1[0], bbox2[0]), max(bbox1[1], bbox2[1]),
                                   min(bbox1[2], bbox2[2]), min(bbox1[3], bbox2[3])])

        if len(intersect_bbox) == 0:
            return 0
        else:
            intersect_width = int(intersect_bbox[0][2]) - int(intersect_bbox[0][0])
            intersect_height = int(intersect_bbox[0][3]) - int(intersect_bbox[0][1])
            if (intersect_width > 0) and (intersect_height > 0):
                intersect_size = float(intersect_width) * float(intersect_height)
                bbox1_size = float(bbox1[3] - bbox1[1]) * float(bbox1[2] - bbox1[0])
                bbox2_size = float(bbox2[3] - bbox2[1]) * float(bbox2[2] - bbox2[0])
                return float(intersect_size / float(bbox1_size + bbox2_size - intersect_size))
            else:
                return 0
