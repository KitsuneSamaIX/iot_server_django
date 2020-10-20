from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse, Http404
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.db.models import FloatField, Avg, Max, Min, Sum, Count
from django.db.models.functions import Cast
from django.db.models.fields.json import KeyTextTransform
import json
import requests
from math import floor
from time import time

from .models import DeviceType, Device, Log


@csrf_exempt
def confirm_token_aws(request):
    """Confirms endpoint ownership.

    :param request: a request containing an 'enableUrl' field in its body.
    :return: HttpResponse.
    """
    body = json.loads(request.body)

    if 'enableUrl' in body:
        requests.get(body['enableUrl'])
    else:
        return HttpResponse(status=400)  # 400 Bad Request

    return HttpResponse(status=200)  # 200 OK


@csrf_exempt
def device_data_dispatcher(request):
    """Dispatches requests to a suitable function.

    :param request: a request containing one of the type specifiers in its header (ex. 'log').
    :return: HttpResponse.
    """
    headers = request.headers

    if 'log' in headers:
        return save_device_log_data(request)

    elif 'shadow' in headers:
        return update_device_shadow_data(request)

    else:
        return HttpResponse(status=400)  # 400 Bad Request


def save_device_log_data(request):
    """Registers a new device log in the database.

    :param request: a request containing (in its body) a set of key fields which uniquely identifies a Device's entry
     and other arbitrary log fields to be saved in the database.
    :return: HttpResponse.
    """
    body = json.loads(request.body)

    try:
        device_serial = body['serial']
        device_kind = body['kind']
        device_model = body['model']
        device_hw = body['hw']

    except KeyError as e:
        print(f"Missing keys in log file: {e}")
        return HttpResponse(status=400)  # 400 Bad Request

    else:
        # identify device and save log file
        device = get_object_or_404(Device, serial_number=device_serial, type__kind=device_kind,
                                   type__model=device_model, type__hardware_version=device_hw)

        Log.objects.create(device=device, reception_datetime=timezone.now(), log_file=body)

    return HttpResponse(status=201)  # 201 Created new Log entry


def update_device_shadow_data(request):
    """Updates/Creates device's (shadow) entry.

    This function will first validate the input parameters,
    then it will search for the device's entry identified by the request's parameters,
    if the entry is found then it will be updated to the new parameters,
    if the device entry is not already in the database it will be created according to the parameters in the request.

    :param request: a request containing a device's shadow data in its body.
    :return: HttpResponse.
    """
    body = json.loads(request.body)

    try:
        # get device's reported info
        device_info = body['state']['reported']['info']
        device_serial = device_info['serial']
        device_kind = device_info['kind']
        device_model = device_info['model']
        device_hw = device_info['hw']
        thing_name = body['thing']

    except KeyError as e:
        print(f"Missing keys in shadow value: {e}")
        return HttpResponse(status=400)  # 400 Bad Request

    else:
        try:
            # Check if the Device specified exists in database
            device = get_object_or_404(Device, serial_number=device_serial, type__kind=device_kind,
                                       type__model=device_model, type__hardware_version=device_hw)

            # Update entry
            device.state = body
            device.save()

            return HttpResponse(status=200)  # 200 OK Entry updated

        except Http404:
            try:
                # Check if the DeviceType specified exists in database
                device_type = get_object_or_404(DeviceType, kind=device_kind, model=device_model,
                                                hardware_version=device_hw)

                # Create a new Device entry for that DeviceType
                Device.objects.create(serial_number=device_serial, type=device_type, registration_datetime=timezone.now(),
                                      aws_thing_name=thing_name, state=body)

                return HttpResponse(status=201)  # 201 Created new Device entry

            except Http404:
                # Write a log and return an http 404 response
                print(f"A device with aws thing name '{thing_name}' sent a shadow update but there was not a Device"
                      f" entry nor a DeviceType matching the request parameters")
                raise


def create_plot(request, pk, attributes):
    """Returns google charts plot displaying displaying attributes variations for a given device.

    This view will search for all logs of a given device(pk), then it will search in each log file to collect the
    specified attributes to fill the google charts template.

    :param request: an http GET request.
    :param pk: primary key of the device.
    :param attributes: names of attributes to be showed on the graph separated by '&' (ex. par1&par2&par3).
    :return: a rendered google charts plot displaying required data.
    """

    if request.method != 'GET':
        return HttpResponse(status=405)  # 405 Method Not Allowed

    # list of strings which will be printed in the webpage in the query performance section
    query_performance_report = []
    t0 = time()  # get start time

    # select all logs of the specified device
    logs = Log.objects.filter(device__pk=pk)

    # check if there are some logs
    if logs.count() == 0:
        raise Http404(f"No logs found for device with pk={pk}")

    # get list of attributes to display
    attr_list = attributes.split('&')

    # header to specify columns' names
    plot_header = ['Date']
    plot_header.extend(attr_list)

    # max number of points to display in graph
    max_points = 100

    # generate input list with points for the plot template
    plot_points = []
    logs = logs.order_by('reception_datetime')
    step = floor(logs.count() / max_points)
    i = step
    for log in logs:
        if i == step:
            # add point(s)
            point = [log.reception_datetime]
            for attr in attr_list:
                try:
                    point.append(log.log_file[attr])

                except KeyError as e:
                    raise Http404(f"Missing attribute {e} in log file.  "
                                  f"LOG: '{log}'  "
                                  f"DEVICE: {log.device}  "
                                  )

            plot_points.append(point)
            i = 0

        else:
            i += 1

    t1 = time()  # get end time
    query_performance_report.append(f'Total number of logs for this device: {logs.count()}')
    query_performance_report.append(f'TOTAL TIME: {t1 - t0} secs')

    # return the rendered webpage
    return render(request, 'iot_backend/plot.html', {
        'plot_header': plot_header,
        'plot_points': plot_points,
        'device_id': Device.objects.get(pk=pk),
        'query_performance_report': query_performance_report,
    })


def aggregate_data(request, actions, pks, attributes):
    """Returns aggregate data based of specified action, devices, attributes.

    The view will display a rendered html page displaying aggregate data for the specified action on specified
    devices for all specified attributes.

    :param request: an http GET request.
    :param actions: names of actions separated by '&' (ex. par1&par2&par3). Currently supported: min, max, avg.
    :param pks: primary keys of devices separated by '&' (ex. pk1&pk2&pk3).
    :param attributes: names of attributes separated by '&' (ex. par1&par2&par3).
    :return: rendered html page with informations required.
    """

    # dictionary of lists of report strings for html template
    dev_report = {}

    if request.method != 'GET':
        return HttpResponse(status=405)  # 405 Method Not Allowed

    # get list of devices' pks as strings and convert them to integer
    pk_list = [int(pk) for pk in pks.split('&')]

    # get list of attributes
    attr_list = attributes.split('&')

    # get list of actions
    act_list = actions.split('&')

    # compile report for each device specified
    for pk in pk_list:
        dev_report[pk] = [str(get_object_or_404(Device, pk=pk))]
        dev_logs = Log.objects.filter(device__pk=int(pk))
        dev_report[pk].append(f"This device has: {dev_logs.count()} logs")
        dev_report[pk].append(f"These are the statistics for the attributes {attr_list}:")

        # compute aggregate data for each attribute specified
        for attr in attr_list:
            dev_report[pk].append(f"[{attr}]:")

            if 'min' in act_list:
                aggr = dev_logs.aggregate(minimum=Min(Cast(KeyTextTransform(attr, 'log_file'),
                                                           output_field=FloatField())))
                dev_report[pk].append(aggr)

            if 'max' in act_list:
                aggr = dev_logs.aggregate(maximum=Max(Cast(KeyTextTransform(attr, 'log_file'),
                                                           output_field=FloatField())))
                dev_report[pk].append(aggr)

            if 'avg' in act_list:
                aggr = dev_logs.aggregate(average=Avg(Cast(KeyTextTransform(attr, 'log_file'),
                                                           output_field=FloatField())))
                dev_report[pk].append(aggr)

    # return the rendered webpage
    return render(request, 'iot_backend/aggregate.html', {
        'dev_report': dev_report,
    })
