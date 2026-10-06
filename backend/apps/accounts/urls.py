from django.urls import path

from . import views

urlpatterns = [
    path("csrf/", views.CsrfView.as_view(), name="auth-csrf"),
    path("login/", views.LoginView.as_view(), name="auth-login"),
    path("logout/", views.LogoutView.as_view(), name="auth-logout"),
    path("me/", views.MeView.as_view(), name="auth-me"),
    path("me/whatsapp/", views.ChangeWhatsappView.as_view(), name="auth-change-whatsapp"),
    path("activation/check/", views.ActivationCheckView.as_view(), name="auth-activation-check"),
    path("activation/complete/", views.ActivationCompleteView.as_view(), name="auth-activation"),
    path("recovery/", views.RecoveryView.as_view(), name="auth-recovery"),
    path("invitations/", views.InvitationView.as_view(), name="auth-invitation"),
    path("users/<int:user_id>/reset/", views.ResetAccessView.as_view(), name="auth-reset"),
]
