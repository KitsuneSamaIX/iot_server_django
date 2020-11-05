"""IoT backend endpoints"""
from django.urls import path

from . import views

urlpatterns = [
    path('', views.confirm_destination_aws),  # endpoint
    path('devices/', views.device_data_dispatcher),  # endpoint
    path('devices/linechart/<int:pk>/<str:attributes>/', views.dev_attrs_line_chart),  # view
    path('devices/columnchart/<str:timeframe>/<str:action>/<int:pk>/<str:attributes>/', views.dev_attrs_aggregate_data_column_chart),  # view
    path('devices/aggregatedata/<str:actions>/<str:pks>/<str:attributes>/', views.devs_attrs_aggregate_data),  # view
]
