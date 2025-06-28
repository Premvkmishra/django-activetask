from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from tasks.views import CustomTokenObtainPairSerializer

class Command(BaseCommand):
    help = 'Test the custom token serializer and user permissions'

    def handle(self, *args, **options):
        # Check user permissions
        users = User.objects.all()
        self.stdout.write("User permissions:")
        for user in users:
            self.stdout.write(f"  {user.username}: is_staff={user.is_staff}, is_superuser={user.is_superuser}")
        
        # Test token serializer for each user
        self.stdout.write("\nTesting token serializer:")
        for user in users:
            # Create a mock request context
            from rest_framework.test import APIRequestFactory
            factory = APIRequestFactory()
            request = factory.post('/')
            request.user = user
            
            # Test the serializer
            serializer = CustomTokenObtainPairSerializer(context={'request': request})
            # We can't fully test without password, but we can check the user object
            self.stdout.write(f"  {user.username}: user.is_staff={user.is_staff}, user.is_superuser={user.is_superuser}")
            
            # Test the validate method manually
            try:
                # This is a simplified test - in real usage, we'd need the password
                self.stdout.write(f"    User ID: {user.id}")
                self.stdout.write(f"    Username: {user.username}")
                self.stdout.write(f"    Is Staff: {user.is_staff}")
                self.stdout.write(f"    Is Superuser: {user.is_superuser}")
            except Exception as e:
                self.stdout.write(f"    Error: {e}") 