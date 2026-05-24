from django.urls import path

from .views import (
    CancelView,
    CheckoutView,
    ListPlansView,
    PortalView,
    ReactivateView,
    StripeWebhookView,
    SubscriptionView,
)

urlpatterns = [
    path("plans", ListPlansView.as_view(), name="billing-plans"),
    path("subscription", SubscriptionView.as_view(), name="billing-subscription"),
    path("checkout", CheckoutView.as_view(), name="billing-checkout"),
    path("portal", PortalView.as_view(), name="billing-portal"),
    path("cancel", CancelView.as_view(), name="billing-cancel"),
    path("reactivate", ReactivateView.as_view(), name="billing-reactivate"),
    path("webhook/stripe", StripeWebhookView.as_view(), name="billing-webhook-stripe"),
]
