import cv2
import google
import numpy


def load_image_from_blob(image_blob_name, image_bucket):
    image_blob = image_bucket.blob(image_blob_name)
    try:
        raw_image = image_blob.download_as_string()
    except google.api_core.exceptions.NotFound:
        return None

    raw_image_bytes = numpy.asarray(bytearray(raw_image), dtype=numpy.uint8)
    if raw_image_bytes.size == 0:
        return numpy.zeros((0, 0, 3), numpy.uint8)

    image = cv2.imdecode(raw_image_bytes, 1)  # cv2.CV_LOAD_IMAGE_COLOR)
    if image is None:
        return numpy.zeros((0, 0, 3), numpy.uint8)

    return image


def load_bgr_image_from_blob_as_rgb(image_blob_name, image_bucket):
    image_bgr = load_image_from_blob(image_blob_name, image_bucket)
    if image_bgr is None:
        return None
    if image_bgr.shape[0] == 0:
        return image_bgr

    image_rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
    return image_rgb
