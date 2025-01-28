from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone

class User(AbstractUser):
    hidden_username = models.CharField(max_length=50, unique=True)
    total_score = models.IntegerField(default=0)
    joined_date = models.DateTimeField(default=timezone.now)
    avg_submission_time = models.FloatField(default=0.0)
    assignments_completed = models.IntegerField(default=0)

    def save(self, *args, **kwargs):
        if not self.username:
            self.username = f"{self.first_name}{self.last_name}"
        if not self.hidden_username:
            import uuid
            self.hidden_username = str(uuid.uuid4())[:8]
        super().save(*args, **kwargs)

    class Meta:
        ordering = ['-total_score']

    def __str__(self):
        return self.username

class Project(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField()
    difficulty = models.IntegerField(choices=[
        (1, 'Easy'),
        (2, 'Medium'),
        (3, 'Hard'),
    ])
    max_score = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class Performance(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    score = models.IntegerField()
    submission_time = models.DateTimeField(default=timezone.now)
    completion_time = models.FloatField(help_text="Time taken to complete in hours")

    class Meta:
        ordering = ['-submission_time']
        unique_together = ['user', 'project']  # One submission per project per user

    def save(self, *args, **kwargs):
        # Update user's statistics
        super().save(*args, **kwargs)
        user = self.user

        # Update total score
        user.total_score = Performance.objects.filter(user=user).aggregate(
            total=models.Sum('score'))['total'] or 0

        # Update assignments completed
        user.assignments_completed = Performance.objects.filter(user=user).count()

        # Update average submission time
        avg_time = Performance.objects.filter(user=user).aggregate(
            avg=models.Avg('completion_time'))['avg'] or 0
        user.avg_submission_time = round(avg_time, 2)

        user.save()

    def __str__(self):
        return f"{self.user.username} - {self.project.name} ({self.score} points)"
