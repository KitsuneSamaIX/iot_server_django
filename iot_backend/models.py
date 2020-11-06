"""Models for iot devices"""
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class DeviceType(models.Model):
    kind = models.CharField(max_length=100, null=False, blank=False)
    model = models.CharField(max_length=100, null=False, blank=False)
    hardware_version = models.CharField(max_length=100, null=False, blank=False)
    data_format = models.JSONField(null=False, blank=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['kind', 'model', 'hardware_version'], name="unique_type"),
        ]

    def __str__(self):
        return f'(pk:{self.pk}) {self.kind} Model:{self.model} HW:{self.hardware_version}'


class Device(models.Model):
    serial_number = models.CharField(max_length=100, null=False, blank=False)
    type = models.ForeignKey(DeviceType, null=False, blank=False, on_delete=models.CASCADE)
    owner = models.ForeignKey(User, null=True, blank=False, on_delete=models.SET_NULL)
    # Note: we pass the callable 'timezone.now' and NOT the fixed value 'timezone.now()', because 'timezone.now()' would be evaluated only ONE time on startup
    registration_datetime = models.DateTimeField(null=False, blank=False, default=timezone.now)
    aws_thing_name = models.CharField(max_length=100, unique=True, null=False, blank=False)
    state = models.JSONField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['serial_number', 'type'], name="unique_device"),
        ]

    def __str__(self):
        return f'(pk:{self.pk}) Serial:{self.serial_number} ({self.type})'


class Log(models.Model):
    device = models.ForeignKey(Device, null=False, blank=False, on_delete=models.CASCADE)
    # Note: we pass the callable 'timezone.now' and NOT the fixed value 'timezone.now()'
    reception_datetime = models.DateTimeField(null=False, blank=False, default=timezone.now)
    log_file = models.JSONField(null=False, blank=False)

    def __str__(self):
        return f'(pk:{self.pk}) {self.reception_datetime} [{self.device}]'
