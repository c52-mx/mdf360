"""Deja la base de QA sin registros capturados, para empezar una ronda de pruebas desde cero.

Se conservan: las cuentas que se indiquen (con su persona y sus roles), los catálogos y la
configuración (roles y permisos, tipos de ofrenda, formularios, aviso de privacidad, procesos de
discipulado, preguntas de peticiones, configuración). Se borra todo lo demás, incluidas la bitácora
y los archivos subidos.

La bitácora es de solo-añadir (NF-03) y sus eventos protegen a sus usuarios: sin borrarla no se
pueden borrar las cuentas. Por eso ``--incluir-bitacora`` es obligatorio al ejecutar: desactiva el
trigger de PostgreSQL solo dentro de la transacción, borra y lo deja activo otra vez. Al final se
registra un evento ``qa.limpieza``.

Es destructivo e irreversible, por eso:
  - sin ``--ejecutar`` solo muestra qué haría (vista previa);
  - para ejecutar exige la variable de entorno ``PERMITIR_LIMPIAR_QA=1`` y ``--incluir-bitacora``;
  - si aparece un modelo que no está clasificado, se detiene sin borrar nada.

    python manage.py limpiar_qa                                  # lista cuentas candidatas
    python manage.py limpiar_qa --conservar "55 1234 5678"       # vista previa
    PERMITIR_LIMPIAR_QA=1 python manage.py limpiar_qa --conservar "55 1234 5678" \
        --incluir-bitacora --ejecutar
"""

import os

from django.apps import apps
from django.core.files.storage import default_storage
from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction
from django.db.models import FileField

from apps.accounts.models import User
from apps.accounts.phone import normalize_whatsapp
from apps.core.models import AuditEvent

# Se conservan completos: catálogos, configuración y piezas de Django.
CONSERVAR = {
    "core.Configuracion",
    "accounts.Rol",
    "accounts.RolEquipo",
    "personas.AvisoPrivacidad",
    "personas.ProcesoDiscipular",
    "grupos.TipoOfrenda",
    "formularios.Formulario",
    "peticiones.FormularioPeticion",
}
DJANGO = {"admin", "auth", "contenttypes", "sessions"}

# Se borran, de los hijos a los padres (así no estorban las claves foráneas protegidas).
# Cada entrada: modelo y, si aplica, cómo conservar lo que pertenece a las cuentas conservadas.
ORDEN = [
    ("core.AuditEvent", None),
    ("muro.Foto", None),
    ("muro.Reporte", None),
    ("muro.Comentario", None),
    ("muro.Reaccion", None),
    ("muro.Audiencia", None),
    ("muro.Publicacion", None),
    ("tablero.Lectura", None),
    ("tablero.Mensaje", None),
    ("notificaciones.Suscripcion", "usuario"),
    ("peticiones.Peticion", None),
    ("grupos.Asistencia", None),
    ("grupos.OfrendaMovimiento", None),
    ("grupos.Ofrenda", None),
    ("grupos.OfrendaIglesiaMovimiento", None),
    ("grupos.OfrendaIglesia", None),
    ("grupos.Reunion", None),
    ("grupos.SolicitudIngreso", None),
    ("grupos.EstudioSemanal", None),
    ("grupos.GrupoMiembro", None),
    ("grupos.Grupo", None),
    ("unidades.UnidadMiembro", None),
    ("unidades.Unidad", None),
    ("personas.PersonaMovimiento", None),
    ("personas.PersonaProceso", None),
    ("personas.Vehiculo", None),
    ("personas.Consentimiento", "persona__usuario"),
    ("personas.Persona", "usuario"),
    ("accounts.ActivationToken", "user"),
    ("accounts.AsignacionRol", "usuario"),
    ("accounts.User", "pk"),
]
BITACORA = "core.AuditEvent"


def _fuera(modelo, campo, usuarios):
    """Registros que NO pertenecen a las cuentas conservadas (los que se borran)."""
    qs = modelo.objects.all()
    if campo is None:
        return qs
    return qs.exclude(**{f"{campo}__in": usuarios})


class Command(BaseCommand):
    help = "Deja la base de QA sin registros capturados (conserva cuentas indicadas y catálogos)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--conservar", action="append", default=[], metavar="WHATSAPP",
            help="WhatsApp de una cuenta que se conserva (se puede repetir).",
        )  # fmt: skip
        parser.add_argument("--ejecutar", action="store_true", help="Borra de verdad.")
        parser.add_argument(
            "--incluir-bitacora", action="store_true",
            help="Autoriza saltar el bloqueo de solo-añadir de la bitácora (obligatorio).",
        )  # fmt: skip

    def handle(self, *args, conservar, ejecutar, incluir_bitacora, **options):
        if not conservar:
            self.stdout.write("Indica qué cuentas conservar con --conservar. Candidatas:")
            candidatas = User.objects.filter(is_superuser=True) | User.objects.filter(
                asignaciones__rol__clave="admin_tecnico"
            )
            for u in candidatas.distinct():
                self.stdout.write(f"  {u.whatsapp}  {u.nombre}  {', '.join(u.roles_clave())}")
            return

        usuarios = []
        for numero in conservar:
            u = User.objects.filter(whatsapp=normalize_whatsapp(numero)).first()
            if not u:
                raise CommandError(f"No existe la cuenta {numero}.")
            usuarios.append(u.pk)

        # Seguridad: todo modelo propio debe estar clasificado; si no, no se borra nada.
        clasificados = CONSERVAR | {nombre for nombre, _ in ORDEN}
        sin_clasificar = [
            m._meta.label
            for m in apps.get_models()
            if m._meta.app_label not in DJANGO and m._meta.label not in clasificados
        ]
        if sin_clasificar:
            raise CommandError(
                "Hay modelos sin clasificar; actualiza el comando: " + ", ".join(sin_clasificar)
            )

        self.stdout.write("Se conservan estas cuentas:")
        for u in User.objects.filter(pk__in=usuarios):
            self.stdout.write(f"  {u.whatsapp}  {u.nombre}  {', '.join(u.roles_clave())}")
        self.stdout.write("\nRegistros que se borran:")
        total = 0
        for nombre, campo in ORDEN:
            modelo = apps.get_model(nombre)
            n = self._candidatos(modelo, campo, usuarios).count()
            total += n
            self.stdout.write(f"  {nombre:<34}{n:>7}")
        self.stdout.write(f"  {'TOTAL':<34}{total:>7}")

        if not ejecutar:
            self.stdout.write("\nVista previa: no se borró nada. Agrega --ejecutar para borrar.")
            return
        if os.environ.get("PERMITIR_LIMPIAR_QA") != "1":
            raise CommandError("Para borrar define PERMITIR_LIMPIAR_QA=1 en este comando.")
        if not incluir_bitacora:
            raise CommandError(
                "Borrar las cuentas exige borrar la bitácora (solo-añadir). Confírmalo con "
                "--incluir-bitacora."
            )

        archivos = []
        with transaction.atomic():
            with connection.cursor() as cursor:
                # Dentro de la transacción: si algo falla, el trigger queda como estaba
                cursor.execute("SET CONSTRAINTS ALL IMMEDIATE")
                cursor.execute("ALTER TABLE core_auditevent DISABLE TRIGGER USER")
            for nombre, campo in ORDEN:
                modelo = apps.get_model(nombre)
                qs = self._candidatos(modelo, campo, usuarios)
                if nombre == BITACORA:
                    with connection.cursor() as cursor:
                        cursor.execute("DELETE FROM core_auditevent")
                    continue
                campos = [f.name for f in modelo._meta.fields if isinstance(f, FileField)]
                for campo_archivo in campos:
                    archivos += [a for a in qs.values_list(campo_archivo, flat=True) if a]
                qs.delete()
            with connection.cursor() as cursor:
                # Las claves foráneas diferidas tienen eventos pendientes: se resuelven antes
                cursor.execute("SET CONSTRAINTS ALL IMMEDIATE")
                cursor.execute("ALTER TABLE core_auditevent ENABLE TRIGGER USER")
            AuditEvent.objects.create(
                action="qa.limpieza",
                actor_repr="limpiar_qa",
                detail={"cuentas_conservadas": conservar},
            )
        borrados = 0
        for ruta in archivos:
            try:
                default_storage.delete(ruta)
                borrados += 1
            except OSError:
                self.stderr.write(f"No se pudo borrar el archivo {ruta}")
        self.stdout.write(f"\nListo: {total} registros y {borrados} archivos borrados.")

    @staticmethod
    def _candidatos(modelo, campo, usuarios):
        if campo == "pk":
            return modelo.objects.exclude(pk__in=usuarios)
        return _fuera(modelo, campo, usuarios)
