# Generated by Django 3.1.2 on 2020-10-20 12:51

from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('iot_backend', '0011_auto_20201020_1249'),
    ]

    operations = [
        migrations.AlterField(
            model_name='device',
            name='registration_datetime',
            field=models.DateTimeField(default=django.utils.timezone.now),
        ),
        migrations.AlterField(
            model_name='log',
            name='reception_datetime',
            field=models.DateTimeField(default=django.utils.timezone.now),
        ),
    ]
