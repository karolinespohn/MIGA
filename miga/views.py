from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model, login
from django.utils import timezone
from django.views.generic import CreateView
from django.urls import reverse_lazy
from datetime import timedelta
from .models import Performance
from .forms import UserRegistrationForm

User = get_user_model()


class SignUpView(CreateView):
    model = User
    form_class = UserRegistrationForm
    template_name = 'registration/signup.html'
    success_url = reverse_lazy('dashboard')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['debug'] = True  # Enable debug information in template
        print("GET context:", context)  # Debug print
        return context

    def post(self, request, *args, **kwargs):
        print("POST data:", request.POST)  # Debug print
        return super().post(request, *args, **kwargs)

    def form_valid(self, form):
        print("Form is valid, saving user...")  # Debug print
        print("Cleaned data:", form.cleaned_data)  # Debug print
        response = super().form_valid(form)
        login(self.request, self.object)  # Log in the user after registration
        return response

    def form_invalid(self, form):
        print("Form validation errors:", form.errors)  # Debug print
        print("POST data during error:", self.request.POST)  # Debug print
        return super().form_invalid(form)


def redirect_to_dashboard(request):
    return redirect('dashboard')


@login_required
def dashboard(request):
    # Mock data for dashboard
    performance_data = {
        'avg_submission_time': request.user.avg_submission_time,
        'assignments_completed': request.user.assignments_completed,
        'total_score': request.user.total_score,
        'ranking_history': [85, 82, 88, 90, 87, 91, 89],  # Mock weekly rankings
        'awards': [
            {'name': 'Early Bird', 'description': 'Push an assignment between  5:00 and 9:00'},
            {'name': 'Steady Sailor', 'description': 'Stay in the same place for 3 consecutive weeks'},
            {'name': 'Tortoise Triumph', 'description': 'Climb to a higher rank 4 weeks in a row'},
            {'name': 'Database Devil', 'description': 'Implement your own main memory database'},
            {'name': 'Night Owl', 'description': 'Push a completed assignment between 23:00 and 5:00'},
            {'name': 'Weekend Warrior', 'description': 'Push a completed assignment on a Saturday or Sunday'},
            {'name': 'Double Down', 'description': 'Push two assignments within 24 hours of each other'},
            {'name': 'Halfway Hero', 'description': 'Complete 50% of all assignment'},
            {'name': 'Momentum Monkey', 'description': 'Stay in the top 5 for 3 consecutive weeks'},
            {'name': 'Lightning Fast', 'description': 'Be the first one to submit a correct assignment'},
            {'name': 'Perfect Score', 'description': 'Pass all tests on an assignment'},
            {'name': 'Demonstration Dodo', 'description': 'Present your work in class'},
        ]
    }
    return render(request, 'miga/dashboard.html', {
        'user': request.user,
        'performance_data': performance_data,
    })


@login_required
def profile(request):
    return render(request, 'miga/profile.html', {
        'user': request.user,
    })

@login_required
def scoreboard(request):
    period = request.GET.get('period', 'week1')
    week_number = int(period.replace('week', ''))

    start_date = timezone.now() - timedelta(weeks=6 - week_number)
    end_date = start_date + timedelta(weeks=1)

    users = User.objects.filter(
        performance__submission_time__gte=start_date,
        performance__submission_time__lt=end_date
    ).distinct()

    # Sort by completion time instead of score
    users = sorted(users, key=lambda u: u.avg_submission_time)
    current_user_rank = next((i + 1 for i, u in enumerate(users) if u == request.user), 0)

    return render(request, 'miga/scoreboard.html', {
        'users': users[:50],
        'current_period': period,
        'current_user_rank': current_user_rank,
    })