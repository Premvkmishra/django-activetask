from rest_framework import serializers
from .models import Project, Task, ActivityLog

class ProjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        fields = ['id', 'title', 'description', 'created_at', 'owner']
        read_only_fields = ['owner', 'created_at']

class TaskSerializer(serializers.ModelSerializer):
    project_title = serializers.CharField(source='project.title', read_only=True)
    
    class Meta:
        model = Task
        fields = ['id', 'title', 'description', 'status', 'due_date', 'created_at', 
                 'assigned_to', 'project', 'project_title']
        read_only_fields = ['created_at']

class ActivityLogSerializer(serializers.ModelSerializer):
    task_title = serializers.CharField(source='task.title', read_only=True)
    
    class Meta:
        model = ActivityLog
        fields = ['id', 'task', 'task_title', 'previous_assignee', 
                 'previous_status', 'previous_due_date', 'updated_at']
        read_only_fields = ['task', 'updated_at'] 