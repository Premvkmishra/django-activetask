from django.db.models.signals import pre_save
from django.dispatch import receiver
from .models import Task, ActivityLog

@receiver(pre_save, sender=Task)
def update_activity_log(sender, instance, **kwargs):
    if instance.pk:  # Only for updates
        try:
            old_task = Task.objects.get(pk=instance.pk)
            if (old_task.assigned_to != instance.assigned_to or 
                old_task.status != instance.status or 
                old_task.due_date != instance.due_date):
                
                ActivityLog.objects.filter(task=old_task).delete()  # Remove old log
                ActivityLog.objects.create(
                    task=old_task,
                    previous_assignee=old_task.assigned_to,
                    previous_status=old_task.status,
                    previous_due_date=old_task.due_date
                )
        except Task.DoesNotExist:
            pass 