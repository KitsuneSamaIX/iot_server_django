# Generated by Django 3.1.2 on 2020-10-09 15:37

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('iot_backend', '0003_auto_20201008_2143'),
    ]

    operations = [
        migrations.AddField(
            model_name='device',
            name='state',
            field=models.JSONField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='devicetype',
            name='data_format',
            field=models.JSONField(default=1),
            preserve_default=False,
        ),
    ]
