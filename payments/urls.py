from django.urls import path
from .views import (
    InitializePaymentView,
    VerifyPaymentView,
    PaystackWebhookView,
    PaystackReturnRedirectView,
)

urlpatterns = [
    path("initialize/", InitializePaymentView.as_view(), name="payment-initialize"),
    path("verify/", VerifyPaymentView.as_view(), name="payment-verify"),
    path("webhook/paystack/", PaystackWebhookView.as_view(), name="paystack-webhook"),
    path("callback/", PaystackReturnRedirectView.as_view(), name="payment-callback"),
]
