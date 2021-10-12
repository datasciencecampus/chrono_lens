import json
import logging


def report_exception(e, variable_names_and_state, request=None, event=None, context=None):
    messages = []
    if event is not None:
        messages.append(f'Event: "{event}"')
    if context is not None:
        messages.append(f'Context: "{context}"')
    if request is not None:
        messages.append(f'Request: "{request}"')

    variables = []
    for variable_name in variable_names_and_state:
        variables.append(f'{variable_name} = "{variable_names_and_state[variable_name]}"')

    message = f"{', '.join(messages)}; Variables: {', '.join(variables)}"

    args_as_strings = [str(a) if type(a) in [int, float, str] else a.__class__.__name__ for a in e.args]
    json_message = f'{e.__class__.__name__}: {",".join(args_as_strings)}'

    logging.exception(message + f'; JSON message="{json_message}"')

    return json.dumps({
        'STATUS': 'Errored',
        'Message': json_message,
        'Arguments': variable_names_and_state
    })
