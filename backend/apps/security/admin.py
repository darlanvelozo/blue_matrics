from django.contrib import admin

from .models import AuditEntry


@admin.register(AuditEntry)
class AuditEntryAdmin(admin.ModelAdmin):
    list_display = ("created_at", "actor_email", "action", "tenant", "ip")
    list_filter = ("action",)
    search_fields = ("actor_email", "tenant__slug", "target_id")
    readonly_fields = (
        "action", "actor", "actor_email", "tenant", "target_type",
        "target_id", "metadata", "ip", "user_agent", "created_at",
    )
    ordering = ("-created_at",)
