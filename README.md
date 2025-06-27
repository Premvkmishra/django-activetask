# Smart Task Tracker (Django + DRF)

## Features
- JWT Authentication (Admin & Contributor roles)
- Projects and Tasks with soft-delete
- Activity Log for task changes
- Pagination, filtering, and export endpoints

## Setup
1. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
2. Make migrations and migrate:
   ```
   python manage.py makemigrations
   python manage.py migrate
   ```
3. Create a superuser:
   ```
   python manage.py createsuperuser
   ```
4. Run the server:
   ```
   python manage.py runserver
   ```

## Deploying Django Backend to Render

1. **Create a new Web Service** on Render and connect your repo.
2. **Set the build and start commands:**
   - **Build Command:**
     ```
     pip install -r requirements.txt
     python manage.py migrate
     ```
   - **Start Command:**
     ```
     gunicorn assignmentt.wsgi:application
     ```
3. **Add environment variables** in Render dashboard:
   - `DJANGO_SECRET_KEY` (set a strong secret key)
   - `DJANGO_DEBUG` = False
   - `ALLOWED_HOSTS` = your Render domain (e.g. `your-app.onrender.com`)
   - `CORS_ALLOWED_ORIGINS` = your frontend URL (e.g. `https://active-task-view.lovable.app`)

4. **Static files:**
   - For production, configure static files with WhiteNoise or S3 (see Django docs).

5. **Update your frontend `.env`** with the deployed backend URL:
   ```
   VITE_API_URL=https://your-app.onrender.com
   ```

## API Endpoints

### Authentication
- `POST /api/token/` - Obtain JWT token
- `POST /api/token/refresh/` - Refresh JWT token

### Projects
- `GET /api/projects/` - List projects (paginated)
- `POST /api/projects/` - Create project (Admin only)
- `GET /api/projects/{id}/` - Retrieve project
- `PUT /api/projects/{id}/` - Update project (Admin only)
- `DELETE /api/projects/{id}/` - Soft delete project (Admin only)

### Tasks
- `GET /api/tasks/` - List tasks (paginated, Admin: all, Contributor: assigned only)
- `POST /api/tasks/` - Create task (Admin only)
- `GET /api/tasks/{id}/` - Retrieve task (Admin/Contributor if assigned)
- `PATCH /api/tasks/{id}/` - Update task status (Contributor if assigned) or full update (Admin)
- `DELETE /api/tasks/{id}/` - Soft delete task (Admin only)
- `GET /api/tasks/export/` - Export tasks (Admin only, JSON)

### Activity Logs
- `GET /api/activity-logs/` - List activity logs (paginated, Admin only)
- `GET /api/activity-logs/{id}/` - Retrieve activity log (Admin only)

## Notes
- Use the JWT token in the `Authorization: Bearer <token>` header for all requests.
- Only one ActivityLog per task is kept, always reflecting the last change.
- For frontend, use any minimal React app to interact with these APIs. 