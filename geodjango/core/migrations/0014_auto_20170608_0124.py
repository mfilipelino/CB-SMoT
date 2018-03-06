# -*- coding: utf-8 -*-
# Generated by Django 1.11.2 on 2017-06-08 01:24
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0013_vehicle_route'),
    ]

    operations = [
        migrations.AlterField(
            model_name='stopbus',
            name='latitude',
            field=models.DecimalField(decimal_places=9, max_digits=11),
        ),
        migrations.AlterField(
            model_name='stopbus',
            name='longitude',
            field=models.DecimalField(decimal_places=9, max_digits=11),
        ),
        migrations.AlterField(
            model_name='trajectory',
            name='latitude',
            field=models.DecimalField(decimal_places=9, max_digits=11),
        ),
        migrations.AlterField(
            model_name='trajectory',
            name='longitude',
            field=models.DecimalField(decimal_places=9, max_digits=11),
        ),
    ]