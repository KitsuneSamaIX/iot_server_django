from django.contrib import admin

from .models import DeviceType, Device, Log

admin.site.register(DeviceType)
admin.site.register(Device)
admin.site.register(Log)
