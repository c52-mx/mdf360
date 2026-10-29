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
    path("users/<int:user_id>/unlock/", views.UnlockAccessView.as_view(), name="auth-unlock"),
    path("accesos/", views.AccesosView.as_view(), name="auth-accesos"),
    path("roles/", views.RolesView.as_view(), name="rbac-roles"),
    path("roles/<slug:clave>/", views.RolView.as_view(), name="rbac-rol"),
    path("roles/<slug:clave>/duplicar/", views.DuplicarRolView.as_view(), name="rbac-rol-copia"),
    path("roles/<slug:clave>/activar/", views.ActivarRolView.as_view(), name="rbac-rol-activar"),
    path(
        "roles/<slug:clave>/desactivar/",
        views.DesactivarRolView.as_view(),
        name="rbac-rol-desactivar",
    ),
    path("permisos/", views.CatalogoPermisosView.as_view(), name="rbac-permisos"),
    path(
        "users/<int:user_id>/permisos/",
        views.PermisosDePersonaView.as_view(),
        name="rbac-permisos-persona",
    ),
    path("users/", views.UsuariosView.as_view(), name="rbac-users"),
    path("users/<int:user_id>/roles/", views.AsignarRolesView.as_view(), name="rbac-assign"),
]
