import requests


def create_authenticated_cloud_function_headers(cloud_function_endpoint):
    # For function to function calls
    # Set up metadata server request
    # See https://cloud.google.com/compute/docs/instances/verifying-instance-identity#request_signature
    metadata_server_token_url = 'http://metadata/computeMetadata/v1/instance/service-accounts/' \
                                'default/identity?audience='
    token_request_url = metadata_server_token_url + cloud_function_endpoint
    token_request_headers = {'Metadata-Flavor': 'Google'}

    # Fetch the token
    token_response = requests.get(token_request_url, headers=token_request_headers)
    json_web_token = token_response.content.decode("utf-8")

    # Provide the token in the request to the receiving function
    receiving_function_headers = {'Authorization': f'bearer {json_web_token}'}
    return receiving_function_headers
