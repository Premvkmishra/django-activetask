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
        print(f"UPDATE method called with HTTP method: {request.method}")
        
        # If it's a PATCH request, handle it as partial_update
        if request.method == 'PATCH':
            return self.partial_update(request, *args, **kwargs)
        
        # Only admins can do full update (PUT requests)
        if not request.user.is_staff:
            return Response({'detail': 'Only admins can fully update tasks.'}, status=status.HTTP_403_FORBIDDEN)
        return super().update(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        print(f"PARTIAL_UPDATE method called with HTTP method: {request.method}")
        print(f"Request path: {request.path}")
        print(f"Request user: {request.user.username} (ID: {request.user.id}, is_staff: {request.user.is_staff})")
        print(f"Request data: {request.data}")
        print(f"Request content type: {request.content_type}")
        
        try:
            # Get the task instance
            instance = self.get_object()
            print(f"Task instance: {instance.id}")
            print(f"Task assigned_to: {instance.assigned_to}")
            print(f"Task assigned_to type: {type(instance.assigned_to)}")
            if instance.assigned_to:
                print(f"Task assigned_to username: {instance.assigned_to.username}")
                print(f"Task assigned_to ID: {instance.assigned_to.id}")
            
            # Check if user is admin or assigned to the task
            if not request.user.is_staff:
                # For contributors, check if they are assigned to this task
                if instance.assigned_to is None:
                    # If task has no assigned_to, only admins can update
                    print(f"Task {instance.id} has no assigned_to, only admins can update")
                    return Response({'detail': 'Only admins can update unassigned tasks.'}, status=status.HTTP_403_FORBIDDEN)
                
                # Compare user IDs for safety
                try:
                    assigned_user_id = instance.assigned_to.id
                    request_user_id = request.user.id
                    print(f"Comparing assigned_user_id: {assigned_user_id} with request_user_id: {request_user_id}")
                    
                    if assigned_user_id != request_user_id:
                        print(f"User {request.user.username} (ID: {request_user_id}) not assigned to task {instance.id} (assigned to: {instance.assigned_to.username} (ID: {assigned_user_id}))")
                        return Response({'detail': 'You can only update tasks assigned to you.'}, status=status.HTTP_403_FORBIDDEN)
                except AttributeError as e:
                    print(f"Error accessing user ID: {e}")
                    return Response({'detail': 'Error accessing task assignment information.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                
                print(f"User {request.user.username} is assigned to task {instance.id}")
            
            # If user is not admin, only allow status updates
            if not request.user.is_staff:
                allowed_fields = {'status'}
                request_fields = set(request.data.keys())
                print(f"Non-admin user requesting fields: {request_fields}")
                print(f"Allowed fields: {allowed_fields}")
                
                if not request_fields.issubset(allowed_fields):
                    print(f"Non-admin user trying to update fields other than status: {request_fields}")
                    return Response({'detail': 'Only admins can update fields other than status.'}, status=status.HTTP_403_FORBIDDEN)
            
            print(f"Proceeding with update for task {instance.id}")
            print(f"Calling parent partial_update with data: {request.data}")
            
            # Call the parent method
            result = super().partial_update(request, *args, **kwargs)
            print(f"Parent partial_update completed successfully")
            return result
            
        except Exception as e:
            print(f"Error in partial_update: {str(e)}")
            import traceback
            traceback.print_exc()
            return Response({'detail': f'Server error: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

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