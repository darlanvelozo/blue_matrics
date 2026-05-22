from django.contrib import admin

from .models import Invoice, Plan, Subscription


@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "price_monthly", "currency", "is_active", "sort_order")
    list_editable = ("is_active", "sort_order")
    list_filter = ("is_active",)
    search_fields = ("code", "name")


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ("tenant", "plan", "status", "trial_ends_at", "current_period_end", "cancel_at_period_end")
    list_filter = ("status", "plan")
    search_fields = ("tenant__slug", "tenant__name", "stripe_customer_id")
    readonly_fields = ("stripe_customer_id", "stripe_subscription_id", "created_at", "updated_at")


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ("tenant", "amount", "currency", "status", "period_end", "paid_at")
    list_filter = ("status", "currency")
    search_fields = ("tenant__slug", "stripe_invoice_id")
