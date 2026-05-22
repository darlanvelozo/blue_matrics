from django.contrib import admin

from .models import Insight


@admin.register(Insight)
class InsightAdmin(admin.ModelAdmin):
    list_display = ("title", "tenant", "kind", "severity", "created_at", "read_at")
    list_filter = ("severity", "kind", "generated_by")
    search_fields = ("title", "narrative", "tenant__slug")
    readonly_fields = ("created_at",)
