from django.contrib import admin

from .models import (
    Category,
    Customer,
    FinancialEntry,
    Product,
    RawPayload,
    Sale,
    SaleItem,
    Salesperson,
    SyncLog,
)


@admin.register(SyncLog)
class SyncLogAdmin(admin.ModelAdmin):
    list_display = ("tenant", "resource", "status", "started_at", "fetched", "upserted", "errors")
    list_filter = ("status", "resource")
    search_fields = ("tenant__slug",)
    readonly_fields = ("started_at", "finished_at")


@admin.register(RawPayload)
class RawPayloadAdmin(admin.ModelAdmin):
    list_display = ("tenant", "resource", "external_id", "fetched_at")
    list_filter = ("resource",)
    readonly_fields = ("payload",)


for m in (Customer, Product, Category, Salesperson, Sale, SaleItem, FinancialEntry):
    admin.site.register(m)
