# Generated by Django 3.1.2 on 2020-10-13 09:33

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('iot_backend', '0004_auto_20201009_1537'),
    ]

    operations = [
        migrations.AddField(
            model_name='device',
            name='thing_name',
            field=models.CharField(default='placeholder', max_length=100),
            preserve_default=False,
        ),
    ]
