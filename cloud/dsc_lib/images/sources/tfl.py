import json

import requests

tfl_json_url = 'https://api.tfl.gov.uk/Place/Type/JamCam'


def filter_image_urls(cameras):
    source_urls = []
    for camera in cameras:
        for additional_property in camera['additionalProperties']:
            if additional_property['key'] == 'imageUrl':
                source_url = additional_property['value']
                source_urls.append(source_url)

    return source_urls


def download_urls():
    response = requests.get(tfl_json_url)
    return json.loads(response.content)
