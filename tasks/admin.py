from django.contrib import admin
from .models import Project, Task, ActivityLog

admin.site.register(Project)
admin.site.register(Task)
admin.site.register(ActivityLog) 