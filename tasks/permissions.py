from rest_framework import permissions

class IsAdminOrReadOnly(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return request.user.is_authenticated
        return request.user.is_authenticated and request.user.is_staff

class IsAssignedContributor(permissions.BasePermission):
    def has_permission(self, request, view):
        # Allow authenticated users to access the view
        return request.user.is_authenticated
    
    def has_object_permission(self, request, view, obj):
        # Contributors can only PATCH their own task's status
        if request.method == 'PATCH':
            return request.user == obj.assigned_to
        # Allow safe methods (GET) only for assigned user
        if request.method in permissions.SAFE_METHODS:
            return request.user == obj.assigned_to
        return False 