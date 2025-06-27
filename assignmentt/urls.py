from django.http import JsonResponse
from django.urls import path, include
from django.contrib import admin

def root(request):
    return JsonResponse({"message": "Django ActiveTask API is running."})

urlpatterns = [
    path('', root),
    path('admin/', admin.site.urls),
    path('api/', include('tasks.urls')),
]