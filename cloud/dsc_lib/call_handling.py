import datetime
import os.path


def extract_request_field(request, field_name):
    request_json = request.get_json()
    request_args = request.args

    if request_json and field_name in request_json:
        field_contents = request_json[field_name]
    elif request_args and field_name in request_args:
        field_contents = request_args[field_name]
    else:
        message = f'"{field_name}" not defined via JSON or arguments in http header'
        print(f'ERROR: {message}')
        raise RuntimeError(message)

    return field_contents


def extract_fields_from_image_blob(blob_name):
    try:
        source, date, time, filename = blob_name.split('/')
        camera_id = os.path.splitext(filename)[0]

        image_date_time = datetime.datetime.strptime(f'{date} {time}', '%Y%m%d %H%M')
    except ValueError as ve:
        raise ValueError('blob name not in format "source/YYYYMMDD/HHMM/camera_id.ext";'
                         f' instead received "{blob_name}"') from ve

    return source, image_date_time, camera_id


def image_blob_name_from_fields(source, date_time, camera_id):
    return f'{source}/{date_time:%Y%m%d}/{date_time:%H%M}/{camera_id}.jpg'
