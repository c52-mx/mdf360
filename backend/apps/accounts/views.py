from django.conf import settings
from django.contrib.auth import login, logout
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.mail import send_mail
from django.middleware.csrf import get_token
from rest_framework import serializers, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView

from apps.core import audit
from apps.personas import services as personas

from . import services
from .models import ActivationToken, Rol, User
from .permissions import requiere
from .phone import normalize_whatsapp


class AuthThrottle(AnonRateThrottle):
    scope = "auth"


class UserSerializer(serializers.ModelSerializer):
    roles = serializers.SerializerMethodField()
    permisos = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "nombre",
            "whatsapp",
            "email",
            "requires_strong_credential",
            "roles",
            "permisos",
        ]

    def get_roles(self, obj) -> list[str]:
        return obj.roles_clave()

    def get_permisos(self, obj) -> list[str]:
        return sorted(obj.permisos())


def _error(code: str, detail: str, http_status: int):
    return Response({"code": code, "detail": detail}, status=http_status)


def _credential_error(exc: DjangoValidationError):
    return _error("weak_credential", " ".join(exc.messages), status.HTTP_400_BAD_REQUEST)


class CsrfView(APIView):
    permission_classes = [AllowAny]
    authentication_classes: list = []

    def get(self, request):
        return Response({"csrfToken": get_token(request)})


class LoginSerializer(serializers.Serializer):
    identifier = serializers.CharField(max_length=254)
    credential = serializers.CharField(max_length=128, trim_whitespace=False)


class LoginView(APIView):
    permission_classes = [AllowAny]
    authentication_classes: list = []
    throttle_classes = [AuthThrottle]

    def post(self, request):
        data = LoginSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        try:
            user = services.authenticate(**data.validated_data, request=request)
        except services.AccountLocked as exc:
            return _error(
                "locked",
                f"Demasiados intentos. Espera {exc.minutes} minutos o pide a tu Líder "
                "que reinicie tu acceso.",
                status.HTTP_429_TOO_MANY_REQUESTS,
            )
        except services.InvalidCredentials:
            return _error(
                "invalid", "Número, correo o PIN incorrectos.", status.HTTP_400_BAD_REQUEST
            )
        login(request, user)
        return Response(UserSerializer(user).data)


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        audit.log("auth.logout", actor=request.user, request=request)
        logout(request)
        return Response(status=status.HTTP_204_NO_CONTENT)


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(UserSerializer(request.user).data)


class ChangeWhatsappSerializer(serializers.Serializer):
    whatsapp = serializers.CharField(max_length=40)
    credential = serializers.CharField(max_length=128, trim_whitespace=False)


class ChangeWhatsappView(APIView):
    """Cambio de número con autoservicio: exige volver a escribir el PIN (decisión 3)."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        data = ChangeWhatsappSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        try:
            user = services.change_whatsapp(
                request.user,
                data.validated_data["whatsapp"],
                data.validated_data["credential"],
                request,
            )
        except services.InvalidCredentials:
            return _error("invalid", "El PIN no es correcto.", status.HTTP_400_BAD_REQUEST)
        except DjangoValidationError as exc:
            return _error("invalid_number", " ".join(exc.messages), status.HTTP_400_BAD_REQUEST)
        except services.DuplicateWhatsapp:
            return _error(
                "duplicate",
                "Ya hay un registro con ese número. Pide a tu Líder que los una.",
                status.HTTP_409_CONFLICT,
            )
        return Response(UserSerializer(user).data)


class TokenSerializer(serializers.Serializer):
    token = serializers.CharField(max_length=200)


class ActivationCheckView(APIView):
    permission_classes = [AllowAny]
    authentication_classes: list = []
    throttle_classes = [AuthThrottle]

    def post(self, request):
        data = TokenSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        try:
            token = services.get_valid_token(data.validated_data["token"])
        except services.InvalidToken:
            return _error("invalid_token", "El enlace no es válido o ya caducó.", 400)
        user = token.user
        return Response(
            {
                "nombre": user.nombre,
                "purpose": token.purpose,
                "requires_strong_credential": user.requires_strong_credential,
            }
        )


class ActivationCompleteSerializer(TokenSerializer):
    credential = serializers.CharField(max_length=128, trim_whitespace=False)
    acepta_privacidad = serializers.BooleanField()
    acepta_foto = serializers.BooleanField(default=False)


class ActivationCompleteView(APIView):
    permission_classes = [AllowAny]
    authentication_classes: list = []
    throttle_classes = [AuthThrottle]

    def post(self, request):
        data = ActivationCompleteSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        if not data.validated_data["acepta_privacidad"]:
            return _error(
                "consent_required", "Debes aceptar el aviso de privacidad para continuar.", 400
            )
        try:
            user = services.complete_activation(
                data.validated_data["token"], data.validated_data["credential"], request
            )
        except services.InvalidToken:
            return _error("invalid_token", "El enlace no es válido o ya caducó.", 400)
        except DjangoValidationError as exc:
            return _credential_error(exc)
        persona = personas.ensure_persona_for_user(user)
        personas.registrar_consentimiento(
            persona,
            acepta_datos=True,
            acepta_foto=data.validated_data["acepta_foto"],
            actor=user,
        )
        login(request, user)
        return Response(UserSerializer(user).data)


class RecoverySerializer(serializers.Serializer):
    identifier = serializers.CharField(max_length=254)


class RecoveryView(APIView):
    """Recuperación gratuita por correo. Responde igual exista o no la cuenta."""

    permission_classes = [AllowAny]
    authentication_classes: list = []
    throttle_classes = [AuthThrottle]

    def post(self, request):
        data = RecoverySerializer(data=request.data)
        data.is_valid(raise_exception=True)
        identifier = data.validated_data["identifier"].strip()
        user = services.find_user(identifier) if "@" in identifier else None
        if user and user.email:
            raw, _ = services.issue_token(user, ActivationToken.Purpose.RESET)
            send_mail(
                "Reinicia tu acceso a MDF360",
                f"Hola {user.nombre.split()[0]},\n\nEntra aquí para elegir un PIN nuevo "
                f"(el enlace caduca en {settings.ACTIVATION_TOKEN_HOURS} horas):\n"
                f"{services.activation_url(raw)}\n\nSi no lo pediste, ignora este mensaje.",
                settings.DEFAULT_FROM_EMAIL,
                [user.email],
            )
            audit.log("auth.recovery_requested", target=user, request=request)
        return Response(
            {
                "detail": "Si el correo está registrado, te enviamos un enlace. "
                "Si no tienes correo, pide a tu Líder que reinicie tu acceso."
            },
            status=status.HTTP_202_ACCEPTED,
        )


class InvitationSerializer(serializers.Serializer):
    whatsapp = serializers.CharField(max_length=40)
    nombre = serializers.CharField(max_length=150)
    email = serializers.EmailField(required=False, allow_blank=True, default="")


def _invite_payload(user, raw, token, reset=False):
    url = services.activation_url(raw)
    return {
        "user": UserSerializer(user).data,
        "activation_url": url,
        "whatsapp_url": services.whatsapp_invite_url(user, url, reset=reset),
        "expires_at": token.expires_at,
    }


class InvitationView(APIView):
    """Crea una cuenta sin PIN y devuelve el enlace para enviarlo por WhatsApp.

    Requiere el permiso usuarios.invitar.
    """

    permission_classes = [requiere("usuarios.invitar")]

    def post(self, request):
        data = InvitationSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        try:
            whatsapp = normalize_whatsapp(data.validated_data["whatsapp"])
        except DjangoValidationError as exc:
            return _error("invalid_number", " ".join(exc.messages), 400)
        user = User.objects.filter(whatsapp=whatsapp).first()
        if user and user.has_usable_password():
            return _error(
                "exists",
                "Esa persona ya tiene cuenta. Usa «Reiniciar acceso».",
                status.HTTP_409_CONFLICT,
            )
        email = data.validated_data["email"]
        if user is None:
            if email and User.objects.filter(email=email.lower()).exists():
                return _error("duplicate_email", "Ese correo ya está en uso.", 409)
            user = User.objects.create_user(
                whatsapp, nombre=data.validated_data["nombre"], email=email
            )
            audit.log("auth.invited", actor=request.user, target=user, request=request)
        personas.ensure_persona_for_user(user)
        raw, token = services.issue_token(user, ActivationToken.Purpose.ACTIVATION, request.user)
        return Response(_invite_payload(user, raw, token), status=status.HTTP_201_CREATED)


class ResetAccessView(APIView):
    """Reinicia el acceso de una persona (perdió su PIN o su número)."""

    permission_classes = [requiere("usuarios.invitar")]

    def post(self, request, user_id: int):
        user = User.objects.filter(pk=user_id, is_active=True).first()
        if user is None:
            return _error("not_found", "No existe la persona.", status.HTTP_404_NOT_FOUND)
        raw, token = services.issue_token(user, ActivationToken.Purpose.RESET, request.user)
        audit.log("auth.reset_issued", actor=request.user, target=user, request=request)
        return Response(_invite_payload(user, raw, token, reset=True))


class RolesView(APIView):
    permission_classes = [requiere("roles.gestionar")]

    def get(self, request):
        return Response(
            [
                {"clave": r.clave, "nombre": r.nombre, "nivel": r.nivel, "permisos": r.permisos}
                for r in Rol.objects.filter(activo=True)
            ]
        )


class UsuariosView(APIView):
    permission_classes = [requiere("roles.gestionar")]

    def get(self, request):
        usuarios = User.objects.filter(is_active=True).order_by("nombre")
        return Response(UserSerializer(usuarios, many=True).data)


class AsignarRolesSerializer(serializers.Serializer):
    roles = serializers.ListField(child=serializers.SlugField(), allow_empty=True)


class AsignarRolesView(APIView):
    permission_classes = [requiere("roles.gestionar")]

    def post(self, request, user_id: int):
        user = User.objects.filter(pk=user_id, is_active=True).first()
        if user is None:
            return _error("not_found", "No existe la persona.", status.HTTP_404_NOT_FOUND)
        data = AsignarRolesSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        try:
            services.asignar_roles(user, data.validated_data["roles"], request.user, request)
        except services.RolNoPermitido:
            return _error(
                "role_not_allowed",
                "No puedes otorgar un rol más alto que el tuyo.",
                status.HTTP_403_FORBIDDEN,
            )
        except DjangoValidationError as exc:
            return _error("invalid_role", " ".join(exc.messages), 400)
        return Response(UserSerializer(user).data)
