from django.contrib import admin
from django.contrib.auth import get_user_model
from .models import Assignment, Performance

User = get_user_model()


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('username', 'hidden_username', 'email', 'is_staff')
    readonly_fields = ('username', 'hidden_username')


@admin.register(Assignment)
class AssignmentAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name', 'description')


@admin.register(Performance)
class PerformanceAdmin(admin.ModelAdmin):
    list_display = ('user', 'assignment', 'score', 'completion_time', 'submission_time')
    list_filter = ('assignment', 'submission_time')
    search_fields = ('user__username', 'assignment__name')
    ordering = ('-submission_time',)

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user', 'assignment')