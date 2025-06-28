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
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.tokens import AccessToken
import logging

# Add logging for debugging
logger = logging.getLogger(__name__)

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
        # Route PATCH requests to partial_update
        if request.method == 'PATCH':
            return self.partial_update(request, *args, **kwargs)
        
        # For PUT requests, check permissions
        if not request.user.is_staff:
            return Response({'detail': 'Only admins can fully update tasks.'}, status=status.HTTP_403_FORBIDDEN)
        
        return super().update(request, *args, **kwargs)

    @action(detail=True, methods=['patch'], permission_classes=[permissions.IsAuthenticated])
    def update_status(self, request, pk=None):
        """
        Special endpoint for contributors to update their own task status.
        Only allows status updates for tasks assigned to the requesting user.
        """
        try:
            # Get the task instance
            task = self.get_object()
            
            # Check if user is admin or assigned to the task
            if not request.user.is_staff:
                # For contributors, check if they are assigned to this task
                if task.assigned_to is None:
                    return Response({'detail': 'Only admins can update unassigned tasks.'}, status=status.HTTP_403_FORBIDDEN)
                
                # Compare user IDs for safety
                if task.assigned_to.id != request.user.id:
                    return Response({'detail': 'You can only update tasks assigned to you.'}, status=status.HTTP_403_FORBIDDEN)
            
            # Validate that only status is being updated
            if not request.user.is_staff:
                allowed_fields = {'status'}
                if not set(request.data.keys()).issubset(allowed_fields):
                    return Response({'detail': 'Only admins can update fields other than status.'}, status=status.HTTP_403_FORBIDDEN)
            
            # Validate status value
            new_status = request.data.get('status')
            if new_status not in ['TODO', 'IN_PROGRESS', 'DONE']:
                return Response({'detail': 'Invalid status value.'}, status=status.HTTP_400_BAD_REQUEST)
            
            # Update the task status
            old_status = task.status
            task.status = new_status
            task.save()
            
            # Create activity log for status change
            ActivityLog.objects.create(
                task=task,
                previous_assignee=task.assigned_to,
                previous_status=old_status,
                previous_due_date=task.due_date
            )
            
            return Response({
                'detail': 'Task status updated successfully',
                'task_id': task.id,
                'old_status': old_status,
                'new_status': new_status
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({'detail': f'Server error: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def partial_update(self, request, *args, **kwargs):
        try:
            # Log the request for debugging
            logger.info(f"User {request.user.username} attempting to update task {kwargs.get('pk')} with data: {request.data}")
            
            # Get the task instance using the filtered queryset
            instance = self.get_object()
            
            # Log the instance found
            logger.info(f"Found task: {instance.id}, assigned to: {instance.assigned_to}")
            
            # If user is not admin, only allow status updates
            if not request.user.is_staff:
                allowed_fields = {'status'}
                if not set(request.data.keys()).issubset(allowed_fields):
                    logger.warning(f"User {request.user.username} tried to update forbidden fields: {request.data.keys()}")
                    return Response(
                        {'detail': 'Only admins can update fields other than status.'}, 
                        status=status.HTTP_403_FORBIDDEN
                    )
                
                # Additional check: ensure user is assigned to this task
                if instance.assigned_to != request.user:
                    logger.warning(f"User {request.user.username} tried to update task not assigned to them")
                    return Response(
                        {'detail': 'You can only update tasks assigned to you.'}, 
                        status=status.HTTP_403_FORBIDDEN
                    )
            
            # Validate the status value if provided
            if 'status' in request.data:
                valid_statuses = ['TODO', 'IN_PROGRESS', 'DONE']  # Adjust based on your model
                if request.data['status'] not in valid_statuses:
                    return Response(
                        {'detail': f'Invalid status. Must be one of: {valid_statuses}'}, 
                        status=status.HTTP_400_BAD_REQUEST
                    )
            
            # Call the parent method
            response = super().partial_update(request, *args, **kwargs)
            logger.info(f"Task {instance.id} updated successfully")
            return response
            
        except Task.DoesNotExist:
            logger.error(f"Task {kwargs.get('pk')} not found for user {request.user.username}")
            return Response(
                {'detail': 'Task not found or you do not have permission to update it.'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Error updating task {kwargs.get('pk')}: {str(e)}", exc_info=True)
            return Response(
                {'detail': f'Server error: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

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

        # Fix the union query - use distinct() to avoid duplicates
        all_tasks = tasks_due_soon.union(tasks_overdue, tasks_completed).distinct()
        
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

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        
        # Add custom claims to token
        token['is_staff'] = user.is_staff
        token['is_superuser'] = user.is_superuser
        token['username'] = user.username
        token['user_id'] = user.id
        
        return token

class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer