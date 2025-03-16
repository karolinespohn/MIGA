from datetime import  time
from django.utils import timezone
from .models import Award, UserAward, User, Performance, BenchmarkMetric, Assignment

# Award definitions
AWARDS = [
    {
        'name': 'Early Bird',
        'description': 'Push an assignment between 5:00 and 9:00'
    },
    {
        'name': 'Steady Sailor',
        'description': 'Stay in the same place for 3 consecutive weeks'
    },
    {
        'name': 'Tortoise Triumph',
        'description': 'Climb to a higher rank 3 weeks in a row'
    },
    {
        'name': 'Database Devil',
        'description': 'Implement your own main memory database'
    },
    {
        'name': 'Night Owl',
        'description': 'Push a completed assignment between 23:00 and 5:00'
    },
    {
        'name': 'Weekend Warrior',
        'description': 'Push a completed assignment on a Saturday or Sunday'
    },
    {
        'name': 'Halfway Hero',
        'description': 'Complete 50% of all assignment'
    },
    {
        'name': 'Winning Whale',
        'description': 'Reach first place'
    },
    {
        'name': 'Momentum Monkey',
        'description': 'Stay in the top 5 for 3 consecutive weeks'
    },
    {
        'name': 'Comeback Kid',
        'description': 'Jump 5 ranks in 1 week'
    },
    {
        'name': 'High Score Horse',
        'description': 'Be in first place for an assignment'
    },
    {
        'name': 'Demonstration Dodo',
        'description': 'Present your work in class'
    },
    {
        'name': 'Punctual Peacock',
        'description': 'Hand in every assignment before the deadline'
    },
    {
        'name': 'Timely Toucan',
        'description': 'Hand in an assignment the day it is due'
    },
    {
        'name': 'Excellent Elephant',
        'description': 'Be in the top 3'
    }
]

def initialize_awards():
    """
    Initialize awards in the database.
    If theres an issue with any awards/if new awards were added & it doens't work as expected, this is often the solution
    """
    for award_data in AWARDS:
        Award.objects.get_or_create(
            name=award_data['name'],
            defaults={'description': award_data['description']}
        )

def check_time_based_award(user, submission_time, start_hour, end_hour, award_name):
    submission_time = submission_time.time()
    start = time(start_hour, 0)
    end = time(end_hour, 0)

    if start <= submission_time <= end:
        award = Award.objects.get(name=award_name)
        UserAward.objects.get_or_create(user=user, award=award)
        return True
    return False

def check_weekend_warrior(user, submission_time):
    """
    checks if the user has anu assignment submitted on a sat/sun
    """
    if submission_time.tzinfo is None:
        submission_time = timezone.make_aware(submission_time)

    weekday = submission_time.weekday()

    performances = Performance.objects.filter(user=user)
    for perf in performances:
        perf_time = perf.submission_time
        if perf_time.tzinfo is None:
            perf_time = timezone.make_aware(perf_time)

        perf_weekday = perf_time.weekday()

        # past submission
        if check_weekday(user, perf_weekday): return True

    # curr submission
    if check_weekday(user, weekday): return True

    return False

def check_weekday(user, day):
    if day >= 5:  # 5 is Saturday, 6 is Sunday
        award = Award.objects.get(name='Weekend Warrior')
        UserAward.objects.get_or_create(user=user, award=award)
        return True


def check_high_score_horse(user, current_rank=None):
    """
    Check if user is in first place for any assignment
    """

    if current_rank == 1:
        award = Award.objects.get(name='High Score Horse')
        UserAward.objects.get_or_create(user=user, award=award)
        return True

    from django.db.models import Q

    assignments = Assignment.objects.all()

    for assignment in assignments:
        import re
        week_match = re.search(r'Week (\d+)', assignment.name)
        if not week_match:
            continue

        week_number = int(week_match.group(1))

        # Check Cpp and Rust
        for language in ['cpp', 'rust']:
            benchmark_pattern_with_underscore = f"BM_W{week_number}_"
            benchmark_pattern_without_underscore = f"BM_W{week_number}"

            users_with_benchmarks = User.objects.filter(
                (Q(benchmarkresult__metrics__benchmark_name__startswith=benchmark_pattern_with_underscore) |
                Q(benchmarkresult__metrics__benchmark_name=benchmark_pattern_without_underscore)) &
                Q(benchmarkresult__language=language)
            ).distinct()

            user_times = {}
            for u in users_with_benchmarks:
                metrics = BenchmarkMetric.objects.filter(
                    Q(benchmark_result__user=u) &
                    Q(benchmark_result__language=language) &
                    (Q(benchmark_name__startswith=benchmark_pattern_with_underscore) |
                    Q(benchmark_name=benchmark_pattern_without_underscore))
                ).order_by('-benchmark_result__submission_time')

                if metrics.exists():
                    user_times[u.id] = metrics.first().cpu_time

            sorted_users = sorted(
                users_with_benchmarks,
                key=lambda us: user_times.get(us.id, float('inf'))
            )

            if sorted_users and sorted_users[0] == user:
                award = Award.objects.get(name='High Score Horse')
                UserAward.objects.get_or_create(user=user, award=award)
                return True

    return False

def check_rank_based_awards(user, current_rank):
    """
    Check for rank-based awards
    """
    if current_rank == 1: # winning whale. others could be added at some point
        award = Award.objects.get(name='Winning Whale')
        UserAward.objects.get_or_create(user=user, award=award)

def check_steady_sailor(user, ranks_history):
    """
    Check if user stayed in same rank for 3 consecutive weeks
    """
    length = 3
    consecutive_ranks = find_sequence(length, ranks_history)

    for sequence in consecutive_ranks:
        if len(set(sequence)) == 1:  # check if all values in sequence are the sme
            award = Award.objects.get(name='Steady Sailor')
            UserAward.objects.get_or_create(user=user, award=award)
            return




def check_tortoise_triumph(user, ranks_history):
    """
    Check if user climbed ranks for 4 consec. weeks
    """

    consecutive_ranks = find_sequence(4, ranks_history)
    for sequence in consecutive_ranks:

        improving = True
        for i in range(len(sequence) - 1):
            if sequence[i] >= sequence[i + 1]:
                improving = False
                break

        if improving:
            award = Award.objects.get(name='Tortoise Triumph')
            UserAward.objects.get_or_create(user=user, award=award)
            return

def check_momentum_monkey(user, ranks_history):
    """
    Check if user stayed in top 5 for 3 consec weeks
    """
    consecutive_ranks = find_sequence(3, ranks_history)

    for sequence in consecutive_ranks:
        if all(rank <= 5 for rank in sequence):  # All ranks in sequence in top 5
            award = Award.objects.get(name='Momentum Monkey')
            UserAward.objects.get_or_create(user=user, award=award)
            return

def check_comeback_kid(user, ranks_history):
    """
    Check if user jumped 5 ranks in 1 week. The number 5 may be too much if not enough people partake in one of the langs
    """
    for i in range(len(ranks_history) - 1):
        current_rank = ranks_history[i]
        next_rank = ranks_history[i + 1]

        if current_rank is not None and next_rank is not None and current_rank > 0 and next_rank > 0:

            rank_improvement = current_rank - next_rank
            if rank_improvement >= 5:
                award = Award.objects.get(name='Comeback Kid')
                UserAward.objects.get_or_create(user=user, award=award)
                return

def check_halfway_hero(user):
    """
    Check if user completed 50% of all assignments.
    """
    total_assignments = Performance.objects.values('assignment').distinct().count()
    user_completed = Performance.objects.filter(user=user).count()

    if user_completed >= total_assignments * 0.5:
        award = Award.objects.get(name='Halfway Hero')
        UserAward.objects.get_or_create(user=user, award=award)

def check_punctual_peacock(user):
    """
    Check if user has submitted all assignments before their deadlines.
    For this it is important that adnins actually set enddates
    """

    user_performances = Performance.objects.filter(user=user)
    user_completed = user_performances.count()

    # Can only be achieved when the last (6th) assignment is submitted
    if user_completed < 6:
        return

    all_on_time = True
    for performance in user_performances:
        assignment = performance.assignment
        if assignment.end_date and performance.submission_time > assignment.end_date:
            all_on_time = False
            break

    if all_on_time:
        award = Award.objects.get(name='Punctual Peacock')
        UserAward.objects.get_or_create(user=user, award=award)

def check_timely_toucan(user, performance=None):
    """
    Check if user has submitted an assignment on the day it is due
    I think this award makes some sense, since it shows 1) they submit assignment on time and 2) they took their time
    I can imagine, that this could lead to people doing it in the last second, though.
    """
    print("\nChecking Timely Toucan award...")

    if performance:
        assignment = performance.assignment
        if not assignment.end_date:
            return

        submission_date = performance.submission_time.date()
        deadline_date = assignment.end_date.date()

        if submission_date == deadline_date:
            award = Award.objects.get(name='Timely Toucan')
            UserAward.objects.get_or_create(user=user, award=award)
    else:
        performances = Performance.objects.filter(user=user)
        for perf in performances:
            assignment = perf.assignment
            if not assignment.end_date:
                continue

            submission_date = perf.submission_time.date()
            deadline_date = assignment.end_date.date()

            if submission_date == deadline_date:
                award = Award.objects.get(name='Timely Toucan')
                UserAward.objects.get_or_create(user=user, award=award)
                return


def check_excellent_elephant(user, current_rank=None):
    """
    Check if user is in the top 3
    """

    if current_rank is not None and current_rank <= 3:
        award = Award.objects.get(name='Excellent Elephant')
        UserAward.objects.get_or_create(user=user, award=award)

def check_database_devil(user):
    """
    Check if user has benchmarks for 6 weeks.
    This implies that the tests for all 6 wekks passed, since the bm stage wouldnt otherwise be reached -> user implemented db
    """
    print("\nChecking Database Devil award...")

    weeks_with_benchmarks = set()

    metrics = BenchmarkMetric.objects.filter(benchmark_result__user=user)

    for metric in metrics:
        import re
        week_match = re.search(r'W(\d+)', metric.benchmark_name)
        if week_match:
            week_number = int(week_match.group(1))
            weeks_with_benchmarks.add(week_number)


    if len(weeks_with_benchmarks) >= 6:
        award = Award.objects.get(name='Database Devil')
        UserAward.objects.get_or_create(user=user, award=award)

def check_awards(user, submission_time=None, ranks_history=None, current_rank=None, performance=None):
    valid_ranks = []
    if ranks_history:
        valid_ranks = [rank for rank in ranks_history if rank is not None]

    if submission_time:
        # early bird
        check_time_based_award(user, submission_time, 5, 9, 'Early Bird')
        # night owl
        check_time_based_award(user, submission_time, 23, 5, 'Night Owl')
        # weekend warrior
        check_weekend_warrior(user, submission_time)

        if performance:
            check_timely_toucan(user, performance)

    if current_rank is not None:
        #winning whale
        check_rank_based_awards(user, current_rank)
        #excellent elephat
        check_excellent_elephant(user, current_rank)

    check_high_score_horse(user, current_rank)

    if valid_ranks:
        # steady sailor
        check_steady_sailor(user, valid_ranks)
        # tortoise triumph
        check_tortoise_triumph(user, valid_ranks)
        #momentum monkey
        check_momentum_monkey(user, valid_ranks)
        #comeback kid
        check_comeback_kid(user, valid_ranks)

    #halfway hero
    check_halfway_hero(user)
    # punctual peacock
    check_punctual_peacock(user)
    # database devil
    check_database_devil(user)
    #timely toucan
    check_timely_toucan(user)

    earned_awards = UserAward.objects.filter(user=user)
    print("\nCurrently earned awards:")
    for user_award in earned_awards:
        print(f"- {user_award.award.name}")

def find_sequence(length, ranks_history):
    consecutive_ranks = []
    current_sequence = []

    for rank in ranks_history:
        if rank is not None and rank > 0:
            current_sequence.append(rank)
        else:
            if len(current_sequence) >= length:
                consecutive_ranks.append(current_sequence[-length:])
            current_sequence = []

    if len(current_sequence) >= length:
        consecutive_ranks.append(current_sequence[-length:])

    return consecutive_ranks
