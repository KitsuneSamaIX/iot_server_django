# Module used for database population testing
from iot_backend.models import DeviceType, Device, Log
from uuid import uuid4
from django.utils import timezone
import json
from random import random, seed
from math import sin, cos

# seed rng
seed()


def create_device_and_populate_logs(n, device_type=DeviceType.objects.get(kind='testlogKind')):
    # create new device
    device = Device.objects.create(serial_number=str(uuid4()), type=device_type, registration_datetime=timezone.now(),
                                   aws_thing_name=f'DeviceTestForLogs{uuid4()}')

    # load test log
    with open('populate_test_log.json', 'r') as f:
        test_log = json.load(f)

    # generate logs on device
    ts = timezone.now().timestamp()
    for i in range(n):
        print(f'progress: {i+1}/{n}')

        # set random values for some attributes
        test_log['ta0'] = int(random() * 1000)
        test_log['ta1'] = int(random() * 1000)
        test_log['ta2'] = cos(i / (n / (3.14 * 2))) * 1000
        test_log['ta3'] = sin(i / (n / (3.14 * 2))) * 1000

        # for each iteration add 10 mins (600 secs)
        log_datetime = timezone.datetime.fromtimestamp((ts + (i*600)), tz=timezone.get_current_timezone())

        Log.objects.create(device=device, reception_datetime=log_datetime, log_file=test_log)
