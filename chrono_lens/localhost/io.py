import json

import cv2
import numpy


def load_from_json(json_file_name):
    with open(json_file_name, 'r') as json_file:
        json_data = json.load(json_file)
    return json_data


def load_from_binary(binary_file_name):
    with open(binary_file_name, 'rb') as binary_file:
        return binary_file.read()


def load_binary_image(image_file_name):
    try:
        raw_image = load_from_binary(image_file_name)
    except FileNotFoundError:
        return None

    raw_image_bytes = numpy.asarray(bytearray(raw_image), dtype=numpy.uint8)
    if raw_image_bytes.size == 0:
        return numpy.zeros((0, 0, 3), numpy.uint8)

    image = cv2.imdecode(raw_image_bytes, 1)  # cv2.CV_LOAD_IMAGE_COLOR)
    if image is None:
        return numpy.zeros((0, 0, 3), numpy.uint8)

    return image


def load_bgr_image_as_rgb(image_file_name):
    image_bgr = load_binary_image(image_file_name)
    if image_bgr is None:
        return None

    if image_bgr.shape[0] == 0:
        return image_bgr

    image_rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
    return image_rgb


def load_bgr_image_as_rgb_if_not_already_loaded(image_rgb, image_file_name):
    if image_rgb is not None:
        return image_rgb

    image_rgb = load_bgr_image_as_rgb(image_file_name)
    if image_rgb is None:
        return None

    if image_rgb.shape[0] == 0:
        return None

    return image_rgb
