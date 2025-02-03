from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from miga.models import Assignment, Performance
import random
from datetime import timedelta

User = get_user_model()

class Command(BaseCommand):
    help = 'Generates mock data for testing'

    def handle(self, *args, **options):
        # Create test projects
        projects = [
            {'name': 'Basic Calculator', 'difficulty': 1, 'max_score': 1},
            {'name': 'Todo App', 'difficulty': 1, 'max_score': 12},
            {'name': 'Weather App', 'difficulty': 2, 'max_score': 3},
            {'name': 'Blog Platform', 'difficulty': 2, 'max_score': 4},
            {'name': 'E-commerce Site', 'difficulty': 3, 'max_score': 5},
        ]

        for project_data in projects:
            Project.objects.get_or_create(
                name=project_data['name'],
                defaults={
                    'description': f"A {project_data['name']} project",
                    'difficulty': project_data['difficulty'],
                    'max_score': project_data['max_score']
                }
            )

        # Create test users
        test_users = []
        for i in range(1, 11):
            user, created = User.objects.get_or_create(
                username=f'user{i}',
                defaults={
                    'email': f'user{i}@example.com',
                    'first_name': f'Test{i}',
                    'last_name': 'User',
                }
            )
            if created:
                user.set_password('testpass123')
                user.save()
            test_users.append(user)

        # Create performances
        projects = Project.objects.all()
        now = timezone.now()

        for user in test_users:
            # Each user completes 2-4 random projects
            for project in random.sample(list(projects), random.randint(2, 4)):
                # Random submission time within last 30 days
                submission_time = now - timedelta(
                    days=random.randint(0, 30),
                    hours=random.randint(0, 23),
                    minutes=random.randint(0, 59)
                )
                
                # Random completion time between 1 and 48 hours
                completion_time = round(random.uniform(1, 48), 1)
                
                # Score based on project difficulty and random performance
                base_score = project.max_score
                score = int(base_score * random.uniform(0.7, 1.0))

                Performance.objects.get_or_create(
                    user=user,
                    project=project,
                    defaults={
                        'score': score,
                        'submission_time': submission_time,
                        'completion_time': completion_time
                    }
                )

        self.stdout.write(self.style.SUCCESS('Successfully generated mock data'))