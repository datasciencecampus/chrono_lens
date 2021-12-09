import asyncio
import json
import logging
import time
from random import uniform

import aiohttp
from aiohttp import ClientError

from chrono_lens.gcloud.authentication import create_authenticated_cloud_function_headers

MAXIMUM_NUMBER_OF_ATTEMPTS = 5


def run_cloud_function_async_with_parameter_list(json_key, json_values, partial_json, endpoint, headers=None,
                                                 sleep_base=16, sleep_tuple=(1, 16)):
    if headers is None:
        headers = create_authenticated_cloud_function_headers(endpoint)

    return asyncio.run(
        _run_cloud_function_with_parameters(
            json_key, json_values, partial_json, endpoint, headers, sleep_base, sleep_tuple))


async def _run_cloud_function_with_parameters(json_key, json_values, partial_json, endpoint, headers, sleep_base,
                                              sleep_tuple):
    async with aiohttp.ClientSession(headers=headers) as session:
        return await asyncio.gather(
            *(_run_cloud_function_with_parameter(json_key, json_value, partial_json, endpoint, session, sleep_base,
                                                 sleep_tuple)
              for json_value in json_values)
        )


async def _run_cloud_function_with_parameter(json_key, json_value, partial_json, endpoint, session, sleep_base,
                                             sleep_tuple):
    logging.debug(f'Processing: "{json_key}": "{json_value}" with {partial_json}')
    complete_json_dict = {json_key: json_value}
    complete_json_dict.update(partial_json)
    text_response = None
    json_response = 'None'

    for attempt_number in range(MAXIMUM_NUMBER_OF_ATTEMPTS):

        start_time = time.time()

        try:
            response = await session.post(endpoint, json=complete_json_dict)

            async with response:
                text_response = await response.text()

                end_time = time.time()

                if response.status == 200:
                    json_response = json.loads(text_response)
                    logging.debug(
                        f'Completed attempt#{attempt_number}: \"{json_key}\": "{json_value}\";'
                        f' response="{json_response}"; elapsed time {end_time - start_time:.2f}s')

                    if json_response['STATUS'] == 'Errored' and json_response['Message'].startswith('ConnectionError'):
                        logging.debug("Retrying due to connection error")
                    else:
                        return json_response

                elif response.status == 401 or response.status == 403:
                    # No point retrying if error is permission denied or similar security issue
                    logging.error(f'Forbidden - not authorised on attempt#{attempt_number}, not retrying:'
                                  f' code={response.status}, json_value="{json_value}"')
                    return {
                        'STATUS': 'Errored',
                        'Message': f'Forbidden - not authorised with "{json_value}"',
                        'TextResponse': text_response,
                        'JsonResponse': json_response
                    }

                logging.debug(
                    f'Failed attempt#{attempt_number}: code={response.status}: "{json_value}";'
                    f' elapsed time {end_time - start_time:.2f}s')

        except ClientError as ce:
            logging.debug(
                f'Failed attempt#{attempt_number}: session.post errored with "{ce}"'
            )

        # No need to wait after the last attempt, we've given up now - so don't waste compute cycles
        if attempt_number < MAXIMUM_NUMBER_OF_ATTEMPTS - 1:
            sleep_time = sleep_base + uniform(*sleep_tuple)
            await asyncio.sleep(sleep_time)
            logging.debug(f"Slept for {sleep_time:.2f}s")

    logging.warning(f'Failed after {MAXIMUM_NUMBER_OF_ATTEMPTS} attempts with "{json_value}"')
    return {
        'STATUS': 'Errored',
        'Message': f'Failed after {MAXIMUM_NUMBER_OF_ATTEMPTS} attempts with "{json_value}"',
        'TextResponse': text_response,
        'JsonResponse': json_response
    }
