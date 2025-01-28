from django.contrib import admin
from django.contrib.auth import get_user_model
from .models import Project, Performance

User = get_user_model()

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('username', 'hidden_username', 'email', 'is_staff')
    readonly_fields = ('username', 'hidden_username')

@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'difficulty', 'max_score', 'created_at')
    list_filter = ('difficulty', 'created_at')
    search_fields = ('name', 'description')
    ordering = ('-created_at',)

@admin.register(Performance)
class PerformanceAdmin(admin.ModelAdmin):
    list_display = ('user', 'project', 'score', 'completion_time', 'submission_time')
    list_filter = ('project', 'submission_time', 'project__difficulty')
    search_fields = ('user__username', 'project__name')
    ordering = ('-submission_time',)
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user', 'project')
