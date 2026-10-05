from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView


class HealthView(APIView):
    """Comprobación de vida para el balanceador y el monitoreo."""

    permission_classes = [AllowAny]
    authentication_classes: list = []

    def get(self, request):
        return Response({"status": "ok"})
