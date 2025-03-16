from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.views.decorators.csrf import csrf_exempt
from rest_framework import status
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .models import BenchmarkResult, BenchmarkMetric, Award, UserAward
from .awards import check_awards, initialize_awards
import re
import json
from math import ceil
from django.db.models import Q


User = get_user_model()


# Helper funs
def get_benchmark_pattern(week_number):
    # my benchmarks are currenly all called BM_W<number>
    # they used to be called BM_W<number>_<description>. both patterns now supported
    return (
        f"BM_W{week_number}_",
        f"BM_W{week_number}"
    )


def get_benchmark_metrics(user=None, week_number=None, language='cpp'):
    pattern_with_underscore, pattern_without_underscore = get_benchmark_pattern(week_number)

    query = Q(benchmark_result__language=language)

    if user:
        query &= Q(benchmark_result__user=user)

    if week_number:
        query &= (
            Q(benchmark_name__startswith=pattern_with_underscore) | 
            Q(benchmark_name=pattern_without_underscore)
        )

    return BenchmarkMetric.objects.filter(query).order_by('-benchmark_result__submission_time')


def get_user_rankings(week_number, language='cpp'):
    """
    Calculate user rankings for a specific week and language.
    """
    pattern_with_underscore, pattern_without_underscore = get_benchmark_pattern(week_number)

    users_with_benchmarks = User.objects.filter(
        (Q(benchmarkresult__metrics__benchmark_name__startswith=pattern_with_underscore) |
        Q(benchmarkresult__metrics__benchmark_name=pattern_without_underscore)) &
        Q(benchmarkresult__language=language)
    ).distinct()

    # Get best time for each user
    user_times = {}
    for user in users_with_benchmarks:
        metrics = get_benchmark_metrics(user=user, week_number=week_number, language=language)
        if metrics.exists():
            user_times[user.id] = metrics.first().cpu_time

    # Sort users by their benchmark times
    sorted_users = sorted(
        users_with_benchmarks,
        key=lambda u: user_times.get(u.id, float('inf'))
    )

    return sorted_users, user_times


def calculate_user_rank(user, sorted_users):
    """ Calculate a user's rank in a list of sorted users.] """
    return next(
        (i + 1 for i, u in enumerate(sorted_users) if u == user),
        None
    )


def calculate_total_score(user, language='cpp'):
    """Calculate total score for a user based on their best benchmark times."""
    total_score = 0
    for week in range(1, 7):
        best_metric = get_benchmark_metrics(user=user, week_number=week, language=language).order_by('cpu_time').first()

        if best_metric:
            # nanoseconds -> milliseconds,  calculate score
            cpu_time_ms = best_metric.cpu_time / 1_000_000
            week_score = 1000 - (cpu_time_ms * 100)
            total_score += ceil(max(0.0, week_score))  # Ensure score doesn't go negative

    return total_score


def redirect_to_dashboard(request):
    return redirect('dashboard')


@login_required
def dashboard(request):
    # language from request, default to last language the user submitted to
    language = request.GET.get('language')

    #  use the language of the user's most recent benchmark
    if not language:
        latest_benchmark = BenchmarkResult.objects.filter(user=request.user).order_by('-submission_time').first()
        language = latest_benchmark.language if latest_benchmark else 'cpp'

    if language not in ['cpp', 'rust']:
        language = 'cpp'

    ranking_history = []
    week_labels = []

    for week in range(1, 7):
        week_labels.append(f"Week {week}")

        sorted_users, user_times = get_user_rankings(week, language)

        ranked_users = [(user.id, user_times.get(user.id, float('inf'))) for user in sorted_users]
        ranked_users.sort(key=lambda x: x[1])

        current_user_rank = None
        for i, (user_id, _) in enumerate(ranked_users, 1):
            if user_id == request.user.id:
                current_user_rank = i
                break

        ranking_history.append(current_user_rank)

    week_labels_js = [str(label) for label in week_labels]

    total_score = calculate_total_score(request.user, language)

    # JSON used for safe use in template
    ranking_history_json = json.dumps(ranking_history)
    week_labels_json = json.dumps(week_labels_js)

    # valc best rank
    valid_ranks = [rank for rank in ranking_history if rank is not None]
    best_rank = min(valid_ranks) if valid_ranks else None

    # calc total rank based on total score for the selected language
    all_users = User.objects.all()
    user_scores = [(user, calculate_total_score(user, language)) for user in all_users]
    sorted_users = sorted(user_scores, key=lambda x: x[1], reverse=True)
    total_rank = next((i + 1 for i, (user, _) in enumerate(sorted_users) if user == request.user), None)

    initialize_awards()

    check_awards(
        user=request.user,
        ranks_history=ranking_history,
        current_rank=total_rank
    )

    all_awards = Award.objects.all()
    for award in all_awards:
        print(f"Award: {award.name}, Image: {award.image_name}")
        earned = UserAward.objects.filter(user=request.user, award=award).exists()
        print(f"Earned: {earned}")

    performance_data = {
        'total_score': total_score,
        'ranking_history': ranking_history_json,
        'week_labels': week_labels_json,
        'best_rank': best_rank,
        'total_rank': total_rank,
        'awards': [
            {
                'name': award.name,
                'description': award.description,
                'image_name': award.image_name,
                'earned': UserAward.objects.filter(user=request.user, award=award).exists()
            }
            for award in Award.objects.all()
        ]
    }

    return render(request, 'miga/dashboard.html', {
        'user': request.user,
        'performance_data': performance_data,
        'current_language': language,
    })

@login_required
def profile(request):
    if request.method == 'POST':
        use_hidden_username = request.POST.get('use_hidden_username') == 'on'
        request.user.use_hidden_username = use_hidden_username
        request.user.save()

    return render(request, 'miga/profile.html', {
        'user': request.user,
    })


@login_required
def scoreboard(request):
    period = request.GET.get('period', 'week1')
    language = request.GET.get('language', 'cpp')

    if language not in ['cpp', 'rust']:
        language = 'cpp'

    week_number = int(period.replace('week', ''))

    sorted_users, user_times = get_user_rankings(week_number, language)

    for user in sorted_users:
        user.user_awards = UserAward.objects.filter(user=user).select_related('award')

    current_user_rank = calculate_user_rank(request.user, sorted_users) or 0

    return render(request, 'miga/scoreboard.html', {
        'users': sorted_users[:10],
        'current_period': period,
        'current_language': language,
        'current_user_rank': current_user_rank,
    })

@api_view(['POST'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
@csrf_exempt
def submit_benchmark(request):
    try:
        initialize_awards()

        language = request.data.get('language', 'cpp')

        if language not in ['cpp', 'rust']:
            return Response({"status": "error", "message": "Invalid language. Must be 'cpp' or 'rust'"},
                           status=status.HTTP_400_BAD_REQUEST)

        benchmark_result = BenchmarkResult.objects.create(
            user=request.user,
            raw_data=request.data.get('raw_data', {}),
            language=language
        )
        benchmarks = request.data.get('raw_data', {}).get('benchmarks', [])

        submitted_week_numbers = []
        for benchmark in benchmarks:
            name = benchmark.get('name', '')
            if name:
                week_match = re.search(r'W(\d+)', name)
                if week_match:
                    week_number = int(week_match.group(1))
                    submitted_week_numbers.append(week_number)
                    assignment_name = f"Week {week_number}"

                    from .models import Assignment
                    assignment, _ = Assignment.objects.get_or_create(
                        name=assignment_name,
                        defaults={'description': f'Assignment for Week {week_number}'}
                    )

                    BenchmarkMetric.objects.create(
                        benchmark_result=benchmark_result,
                        benchmark_name=name,
                        assignment=assignment,
                        cpu_time=benchmark.get('cpu_time', 0),
                        real_time=benchmark.get('real_time', 0),
                        iterations=benchmark.get('iterations', 0)
                    )

        current_week = max(submitted_week_numbers) if submitted_week_numbers else 1

        sorted_users, _ = get_user_rankings(current_week, language)

        current_rank = calculate_user_rank(request.user, sorted_users) or 0

        ranks_history = []
        for week in range(1, 7):
            week_sorted_users, _ = get_user_rankings(week, language)

            rank = calculate_user_rank(request.user, week_sorted_users)
            if rank:
                ranks_history.append(rank)

        check_awards(
            user=request.user,
            submission_time=benchmark_result.submission_time,
            ranks_history=ranks_history,
            current_rank=current_rank
        )

        return Response({"status": "success", "message": "Benchmark results recorded"},
                        status=status.HTTP_201_CREATED)

    except Exception as e:
        return Response({"status": "error", "message": str(e)},
                        status=status.HTTP_400_BAD_REQUEST)
