from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from django.utils import timezone
from datetime import timedelta
from .models import Project, Task, ActivityLog
from .serializers import ProjectSerializer, TaskSerializer, ActivityLogSerializer
from .permissions import IsAdminOrReadOnly, IsAssignedContributor
from django.contrib.auth.models import User
from rest_framework import serializers, permissions
from rest_framework.permissions import OR
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.tokens import AccessToken

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
            return [permissions.IsAuthenticated()]
        if self.action in ['partial_update']:
            # Allow contributors to PATCH their own tasks, admins can PATCH any task
            return [permissions.IsAuthenticated()]
        return [IsAdminOrReadOnly()]

    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return Task.objects.filter(is_deleted=False)
        return Task.objects.filter(is_deleted=False, assigned_to=user)

    def perform_destroy(self, instance):
        instance.is_deleted = True
        instance.save()

    def update(self, request, *args, **kwargs):
        # Only admins can do full update
        if not request.user.is_staff:
            return Response({'detail': 'Only admins can fully update tasks.'}, status=status.HTTP_403_FORBIDDEN)
        return super().update(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        # Get the task instance
        instance = self.get_object()
        
        # Check if user is admin or assigned to the task
        if not request.user.is_staff and instance.assigned_to != request.user:
            return Response({'detail': 'You can only update tasks assigned to you.'}, status=status.HTTP_403_FORBIDDEN)
        
        # If user is not admin, only allow status updates
        if not request.user.is_staff:
            allowed_fields = {'status'}
            if not set(request.data.keys()).issubset(allowed_fields):
                return Response({'detail': 'Only admins can update fields other than status.'}, status=status.HTTP_403_FORBIDDEN)
        
        return super().partial_update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        if not request.user.is_staff:
            return Response({'detail': 'Only admins can delete tasks.'}, status=status.HTTP_403_FORBIDDEN)
        return super().destroy(request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        if not request.user.is_staff:
            return Response({'detail': 'Only admins can create tasks.'}, status=status.HTTP_403_FORBIDDEN)
        return super().create(request, *args, **kwargs)

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
    permission_classes = [permissions.IsAdminUser]

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username']

class UserViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAdminUser]

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def current_user(request):
    serializer = UserSerializer(request.user)
    return Response(serializer.data)

class CustomAccessToken(AccessToken):
    def __init__(self, user=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if user:
            self['is_staff'] = user.is_staff
            self['is_superuser'] = user.is_superuser
            self['username'] = user.username
            self['user_id'] = user.id

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        data = super().validate(attrs)
        
        # Create a custom access token with additional claims
        access_token = CustomAccessToken(user=self.user)
        
        # Replace the access token in the response
        data['access'] = str(access_token)
        
        return data

class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer 