from django.contrib import admin

from .models import Tenant


@admin.register(Tenant)
class TenantAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "status", "trial_ends_at", "created_at")
    list_filter = ("status",)
    search_fields = ("name", "slug", "cnpj")
    readonly_fields = ("public_id", "created_at", "updated_at")
