from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from datetime import timedelta
from .models import Project, Task, ActivityLog
from .serializers import ProjectSerializer, TaskSerializer, ActivityLogSerializer
from .permissions import IsAdminOrReadOnly, IsAssignedContributor

class ProjectViewSet(viewsets.ModelViewSet):
    queryset = Project.objects.filter(is_deleted=False)
    serializer_class = ProjectSerializer
    permission_classes = [IsAdminOrReadOnly]

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

    def perform_destroy(self, instance):
        instance.is_deleted = True
        instance.save()

class TaskViewSet(viewsets.ModelViewSet):
    queryset = Task.objects.filter(is_deleted=False)
    serializer_class = TaskSerializer
    
    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [(IsAssignedContributor | IsAdminOrReadOnly)()]
        return [IsAdminOrReadOnly()]

    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return Task.objects.filter(is_deleted=False)
        return Task.objects.filter(is_deleted=False, assigned_to=user)

    def perform_destroy(self, instance):
        instance.is_deleted = True
        instance.save()

    @action(detail=False, methods=['get'], permission_classes=[IsAdminOrReadOnly])
    def export(self, request):
        tasks_due_soon = Task.objects.filter(
            is_deleted=False,
            due_date__lte=timezone.now() + timedelta(hours=48),
            due_date__gte=timezone.now()
        )
        
        tasks_overdue = Task.objects.filter(
            is_deleted=False,
            due_date__lt=timezone.now(),
            status__in=['TODO', 'IN_PROGRESS']
        )
        
        tasks_completed = Task.objects.filter(
            is_deleted=False,
            status='DONE',
            due_date__gte=timezone.now() - timedelta(hours=24)
        )

        serializer = TaskSerializer(
            tasks_due_soon.union(tasks_overdue, tasks_completed),
            many=True
        )
        return Response({
            'due_soon': TaskSerializer(tasks_due_soon, many=True).data,
            'overdue': TaskSerializer(tasks_overdue, many=True).data,
            'completed_recently': TaskSerializer(tasks_completed, many=True).data
        })

class ActivityLogViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ActivityLog.objects.all()
    serializer_class = ActivityLogSerializer
    permission_classes = [IsAdminOrReadOnly] 