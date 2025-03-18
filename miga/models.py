import random

from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver
from rest_framework.authtoken.models import Token

class User(AbstractUser):
    hidden_username = models.CharField(max_length=50, unique=True)
    use_hidden_username = models.BooleanField(default=False)
    total_score = models.IntegerField(default=0)
    joined_date = models.DateTimeField(default=timezone.now)
    assignments_completed = models.IntegerField(default=0)

    def save(self, *args, **kwargs):
        if not self.username:
            self.username = f"{self.first_name}{self.last_name}"
        if not self.hidden_username:
            self.hidden_username = self._generate_unique_hidden_username()
        super().save(*args, **kwargs)

    class Meta:
        ordering = ['-total_score']

    def __str__(self):
        return self.username

    @property
    def display_name(self):
        """
        returns either the real username or hidden username based on user preference
        """
        return self.hidden_username if self.use_hidden_username else self.username

    def _generate_unique_hidden_username(self):
        """
        Generate a unique hidden username
        """
        adjectives = ["Supportive", "Frantic", "Beautiful", "Chaotic", "Chubby", "Bald", "Clean", "Elegant", "Scruffy",
                      "Unkempt", "Agreeable", "Ambitious", "Jolly", "Witty", "Clumsy", "Thoughtless", "Chatty", "Gothic",
                      "Mischievous", "Cautious"]
        animals = ["Cow", "Gorilla", "Antelope", "Bat", "Whale", "Butterfly", "Goldfish", "Crocodile", "Lion", "Sheep",
                   "Turtle", "Panda", "Ladybug", "Chicken", "Hippo", "Wolf", "Grasshopper", "Crab", "Jellyfish", "Moose",
                   "Elephant", "Giraffe"]

        # since they are randomly generated, it may take a few tries to find name that isnt used yet.
        # for current class size, it should usually work in 1 try, 2 at most. i put 100 just to be sure
        attempts = 0
        max_attempts = 100

        while attempts < max_attempts:
            adjective = random.choice(adjectives)
            animal = random.choice(animals)

            hidden_username = f"{adjective}{animal}"

            # check if this combination already exists
            if not User.objects.filter(hidden_username=hidden_username).exists():
                return hidden_username

            attempts += 1

        # If we couldn't find a unique combination after max_attempts, we append a random number
        # this will probably never happen.
        while True:
            adjective = random.choice(adjectives)
            animal = random.choice(animals)
            random_number = random.randint(1, 9999)

            hidden_username = f"{adjective}{animal}{random_number}"

            if not User.objects.filter(hidden_username=hidden_username).exists():
                return hidden_username

class Assignment(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField()
    end_date = models.DateTimeField(null=True, blank=True, help_text="Optional. If set, benchmarks for this assignment won't be updated after this date.")

    def __str__(self):
        return self.name


class Performance(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    assignment = models.ForeignKey(Assignment, on_delete=models.CASCADE)
    score = models.IntegerField()
    submission_time = models.DateTimeField(default=timezone.now)
    completion_time = models.FloatField(help_text="Time taken to complete in hours")
    cpu_time = models.FloatField(null=True, help_text="CPU time in nanoseconds")

    class Meta:
        ordering = ['-submission_time']
        unique_together = ['user', 'assignment']  # One submission per assignment per user. old submissions discarded when new ones are pushed

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        user = self.user

        user.total_score = Performance.objects.filter(user=user).aggregate(
            total=models.Sum('score'))['total'] or 0

        user.assignments_completed = Performance.objects.filter(user=user).count()

        user.save()

    def __str__(self):
        return f"{self.user.username} - {self.assignment.name} ({self.score} points)"

# Auto-create tokens for users
@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_auth_token(sender, instance=None, created=False, **kwargs):
    if created:
        Token.objects.create(user=instance)


class BenchmarkResult(models.Model):
    LANGUAGE_CHOICES = [
        ('cpp', 'C++'),
        ('rust', 'Rust'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    submission_time = models.DateTimeField(auto_now_add=True)
    raw_data = models.JSONField()  # Stores full benchmark JSON
    language = models.CharField(max_length=10, choices=LANGUAGE_CHOICES, default='cpp')

    def __str__(self):
        return f"{self.user.username} benchmark result from {self.submission_time}"


class Award(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField()
    image_name = models.CharField(max_length=100, editable=False)

    def save(self, *args, **kwargs):
        # image names are always the name of the reward in lowercase, with the whitespaces replaced by -
        self.image_name = self.name.lower().replace(' ', '-')
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class UserAward(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='awards')
    award = models.ForeignKey(Award, on_delete=models.CASCADE)
    earned_date = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['user', 'award']

    def __str__(self):
        return f"{self.user.username} - {self.award.name}"


class BenchmarkMetric(models.Model):
    benchmark_result = models.ForeignKey(BenchmarkResult, on_delete=models.CASCADE, related_name='metrics')
    benchmark_name = models.CharField(max_length=255)
    assignment = models.ForeignKey(Assignment, on_delete=models.CASCADE)
    cpu_time = models.FloatField()
    real_time = models.FloatField()
    iterations = models.IntegerField()

    class Meta:
        unique_together = ['benchmark_result', 'benchmark_name']

    def save(self, *args, **kwargs):
        # gets week number
        import re
        week_match = re.search(r'W(\d+)', self.benchmark_name)
        if week_match:
            week_number = int(week_match.group(1))
            assignment_name = f"Week {week_number}"

            self.assignment, _ = Assignment.objects.get_or_create(
                name=assignment_name,
                defaults={'description': f'Assignment for Week {week_number}'}
            )

        super().save(*args, **kwargs)

        self.update_performance()

    def update_performance(self):
        # Check if assignment has an end date and if it has passed
        if self.assignment.end_date and self.assignment.end_date < timezone.now():
            # Assignment has ended, don't update benchmarks
            # this is especially necessary, for weeks 5 and 6
            return

        performance, created = Performance.objects.get_or_create(
            user=self.benchmark_result.user,
            assignment=self.assignment,
            defaults={'score': 0, 'completion_time': 0, 'cpu_time': self.cpu_time}
        )

        metric = BenchmarkMetric.objects.filter(
            assignment=self.assignment,
            benchmark_name=self.benchmark_name
        ).order_by('cpu_time')

        if metric:
            time = metric.first().cpu_time
            performance.score = time
            performance.cpu_time = time
            performance.save()
