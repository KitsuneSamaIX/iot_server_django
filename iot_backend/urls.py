"""IoT backend endpoints"""
from django.urls import path

from . import views

urlpatterns = [
    path('', views.confirm_token_aws),  # endpoint
    path('devices/', views.device_data_dispatcher),  # endpoint
    path('devices/plot/<int:pk>/<str:attributes>/', views.create_plot),  # view
    path('devices/<str:actions>/<str:pks>/<str:attributes>/', views.aggregate_data),  # view
]
