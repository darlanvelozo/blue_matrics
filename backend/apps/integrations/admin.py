from django.contrib import admin

from .models import ContaAzulConnection, OAuthState


@admin.register(ContaAzulConnection)
class ContaAzulConnectionAdmin(admin.ModelAdmin):
    list_display = ("tenant", "status", "expires_at", "connected_at", "last_synced_at")
    list_filter = ("status",)
    search_fields = ("tenant__slug", "tenant__name")
    readonly_fields = (
        "access_token_enc",
        "refresh_token_enc",
        "created_at",
        "updated_at",
    )


@admin.register(OAuthState)
class OAuthStateAdmin(admin.ModelAdmin):
    list_display = ("state", "tenant", "initiated_by_email", "created_at", "consumed_at")
    search_fields = ("tenant__slug", "initiated_by_email")
    readonly_fields = ("created_at", "consumed_at")
