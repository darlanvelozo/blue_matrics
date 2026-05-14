from django.contrib import admin

from .models import Membership, User


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ("email", "full_name", "is_active", "is_staff", "date_joined")
    search_fields = ("email", "full_name")
    readonly_fields = ("public_id", "date_joined", "last_login")


@admin.register(Membership)
class MembershipAdmin(admin.ModelAdmin):
    list_display = ("user", "tenant", "role", "is_active", "created_at")
    list_filter = ("role", "is_active")
    search_fields = ("user__email", "tenant__slug", "tenant__name")
