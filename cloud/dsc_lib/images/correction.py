import cv2
import numpy as np

"""
Maximum image dimension of 440 was determined by manual testing. This blurred number plates of cars and faces to
reduce chance of accidental disclosure, in the rare circumstance when such items were close to the camera.
This is in place of more sophisticated number plate recognition etc.
"""
IMAGE_MAX_AXIS_THRESHOLD = 440


def resize_jpeg_image(jpeg_raw_data, image_max_axis_threshold):
    if jpeg_raw_data is None:
        return None

    jpeg_image_bytes = np.asarray(bytearray(jpeg_raw_data), dtype="uint8")
    if jpeg_image_bytes.size == 0:
        return None

    jpeg_image = cv2.imdecode(jpeg_image_bytes, cv2.IMREAD_COLOR)

    if jpeg_image is None:
        return None

    major_axis = max(jpeg_image.shape)

    # If image's largest axis is smaller than threshold, no work required; just
    # return the encoded JPEG data (don't re-encode it)
    if major_axis <= image_max_axis_threshold:
        return jpeg_raw_data

    new_scale_factor = image_max_axis_threshold / major_axis

    new_image_width = int(jpeg_image.shape[1] * new_scale_factor)
    new_image_height = int(jpeg_image.shape[0] * new_scale_factor)

    resized_image = cv2.resize(jpeg_image, (new_image_width, new_image_height),
                               interpolation=cv2.INTER_AREA)

    resized_return_code, resized_encoded_array = cv2.imencode('.jpg', resized_image)

    # convert the array to bytes
    resized_encoded_bytes = resized_encoded_array.tobytes()

    return resized_encoded_bytes
