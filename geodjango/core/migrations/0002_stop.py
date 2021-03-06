# -*- coding: utf-8 -*-
# Generated by Django 1.11.2 on 2017-06-03 23:03
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Stop',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('latitude', models.DecimalField(decimal_places=20, max_digits=25)),
                ('longitude', models.DecimalField(decimal_places=20, max_digits=25)),
                ('code', models.IntegerField()),
                ('name', models.CharField(max_length=100)),
                ('address', models.CharField(max_length=200)),
                ('route', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='core.Route')),
            ],
        ),
    ]
