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
from datetime import datetime
import boto3

from .models import DeviceType, Device, Log


@csrf_exempt
def confirm_destination_aws(request):
    """Confirms endpoint ownership and sets aws destination status as 'ENABLED'.

    :param request: A request containing a 'confirmationToken' field in its body.
    :return: HttpResponse.
    """
    body = json.loads(request.body)

    if 'confirmationToken' in body:
        client = boto3.client('iot')
        client.confirm_topic_rule_destination(confirmationToken=body['confirmationToken'])
        client.update_topic_rule_destination(
            arn=body['arn'],
            status='ENABLED'
        )

    else:
        return HttpResponse(status=400)  # 400 Bad Request

    return HttpResponse(status=200)  # 200 OK


@csrf_exempt
def device_data_dispatcher(request):
    """Dispatches requests to a suitable function.

    :param request: A request containing one of the type specifiers in its header (ex. 'log').
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

    :param request: A request containing (in its body) a set of key fields which uniquely identifies a Device's entry
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

    :param request: A request containing a device's shadow data in its body.
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


def dev_attrs_line_chart(request, pk, attributes):
    """Returns a rendered google charts template displaying attributes variations for a given device.

    This view will search for all logs of a given device(pk), then it will search in each log file to collect the
    specified attributes to fill the google charts template.

    :param request: An http GET request.
    :param pk: Primary key of the device.
    :param attributes: Names of attributes to be showed on the graph separated by '&' (ex. attr1&attr2&attr3).
    :return: A rendered google charts' line chart displaying required data.
    """

    if request.method != 'GET':
        return HttpResponse(status=405)  # 405 Method Not Allowed

    # list of strings which will be printed in the webpage in the query performance section
    query_performance_report = []
    t0 = time()  # get start time

    # select all logs of the specified device
    logs = Log.objects.filter(device__pk=pk)

    # check if there are some logs
    if not logs.exists():
        raise Http404(f"No logs found for device with pk={pk}")

    # get list of attributes to display
    attr_list = attributes.split('&')

    # header to specify columns' names
    chart_header = ['Date']
    chart_header.extend(attr_list)

    # max number of points to display in graph
    max_points = 100

    # generate input list with points for the chart template
    chart_points = []
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

            chart_points.append(point)
            i = 0

        else:
            i += 1

    t1 = time()  # get end time
    query_performance_report.append(f'Total number of logs for this device: {logs.count()}')
    query_performance_report.append(f'TOTAL TIME: {t1 - t0} secs')

    # return the rendered webpage
    return render(request, 'iot_backend/line_chart.html', {
        'chart_header': chart_header,
        'chart_points': chart_points,
        'device_id': Device.objects.get(pk=pk),
        'query_performance_report': query_performance_report,
    })


def dev_attrs_aggregate_data_column_chart(request, timeframe, action, pk, attributes):
    """Displays attributes' aggregate data variations for a given device on a given timeframe.

    This view returns a rendered google charts' column chart template displaying attributes' aggregate data variations
    of the specified action for a given device on a given timeframe.

    :param request: An http GET request.
    :param timeframe: The desired timeframe name. Currently supported: year, month, day.
    :param action: Names of action. Currently supported: min, max, avg.
    :param pk: Primary key of the device.
    :param attributes: Names of attributes separated by '&' (ex. attr1&attr2&attr3).
    :return: A rendered google charts' column chart displaying required data.
    """

    if request.method != 'GET':
        return HttpResponse(status=405)  # 405 Method Not Allowed

    # validate parameters passed
    if ((timeframe not in ['year', 'month', 'day']) or
            (action not in ['min', 'max', 'avg']) or
            not (Log.objects.filter(device__pk=pk).exists())):

        raise Http404()

    # get list of attributes to compare
    attr_list = attributes.split('&')

    # get all logs from specified device
    logs = Log.objects.filter(device__pk=pk)

    # create chart description
    chart_title = f"Statistics for device: '{get_object_or_404(Device, pk=pk)}'."
    chart_subtitle = f"Showing variation of {action} values for {attr_list} attributes per {timeframe}."

    # create chart header
    chart_header = [timeframe]
    attr_list_for_header = [f'{action} {attr}' for attr in attr_list]
    chart_header.extend(attr_list_for_header)

    # group and order by specified timeframe
    if timeframe == 'year':
        logs = logs.values_list('reception_datetime__year')
        logs = logs.order_by('reception_datetime__year')

    elif timeframe == 'month':
        logs = logs.values_list('reception_datetime__year', 'reception_datetime__month')
        logs = logs.order_by('reception_datetime__year', 'reception_datetime__month')

    elif timeframe == 'day':
        logs = logs.values_list('reception_datetime__year', 'reception_datetime__month', 'reception_datetime__day')
        logs = logs.order_by('reception_datetime__year', 'reception_datetime__month', 'reception_datetime__day')

    # get aggregate data of specified attributes (on specified timeframe defined above)
    for attr in attr_list:
        if action == 'min':
            logs = logs.annotate(**{f'minimum_{attr}': Min(Cast(KeyTextTransform(attr, 'log_file'), output_field=FloatField()))})

        elif action == 'max':
            logs = logs.annotate(**{f'maximum_{attr}': Max(Cast(KeyTextTransform(attr, 'log_file'), output_field=FloatField()))})

        elif action == 'avg':
            logs = logs.annotate(**{f'average_{attr}': Avg(Cast(KeyTextTransform(attr, 'log_file'), output_field=FloatField()))})

    # adjust logs' QuerySet tuples for the chart template
    chart_points = []
    for t in logs:
        if timeframe == 'year':
            new_t = (datetime(t[0], 1, 1),) + t[1:]

        if timeframe == 'month':
            new_t = (datetime(t[0], t[1], 1),) + t[2:]

        elif timeframe == 'day':
            new_t = (datetime(t[0], t[1], t[2]),) + t[3:]

        chart_points.append(new_t)

    # return the rendered webpage
    return render(request, 'iot_backend/column_chart.html', {
        'chart_title': chart_title,
        'chart_subtitle': chart_subtitle,
        'chart_header': chart_header,
        'chart_points': chart_points,
        'logs_num': Log.objects.filter(device__pk=pk).count(),  # this query impacts performances and it is here only for testing purposes
    })


def devs_attrs_aggregate_data(request, actions, pks, attributes):
    """Returns aggregate data based of specified action, devices, attributes.

    The view will display a rendered html text page displaying aggregate data for the specified actions on specified
    devices for all specified attributes.

    :param request: An http GET request.
    :param actions: Names of actions separated by '&' (ex. act1&act2&act3). Currently supported: min, max, avg.
    :param pks: Primary keys of devices separated by '&' (ex. pk1&pk2&pk3).
    :param attributes: Names of attributes separated by '&' (ex. attr1&attr2&attr3).
    :return: Rendered html page with informations required.
    """

    if request.method != 'GET':
        return HttpResponse(status=405)  # 405 Method Not Allowed

    # dictionary of lists of report strings for html template
    dev_report = {}

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
    return render(request, 'iot_backend/aggregate_data.html', {
        'dev_report': dev_report,
    })
