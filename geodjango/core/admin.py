# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from django.contrib import admin

from .models import Trajectory

@admin.register(Trajectory)
class TrajectoryAdmin(admin.ModelAdmin):
    list_display = ('id',)


