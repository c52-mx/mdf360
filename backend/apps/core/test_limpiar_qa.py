import io

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import connection, transaction

from apps.accounts.models import AsignacionRol, Rol, User
from apps.core.models import AuditEvent
from apps.grupos.models import Grupo, GrupoMiembro, TipoOfrenda
from apps.muro.models import Audiencia, Publicacion
from apps.personas import services as personas
from apps.personas.models import Persona


def cuenta(whatsapp, nombre, rol):
    user = User.objects.create_user(whatsapp, nombre=nombre)
    AsignacionRol.objects.create(usuario=user, rol=Rol.objects.get(clave=rol))
    personas.ensure_persona_for_user(user)
    return user


@pytest.fixture
def datos(db):
    qa = cuenta("55 0000 0001", "Super Usuario QA", "admin_tecnico")
    pastor = cuenta("55 0000 0002", "Pastor", "pastor")
    grupo = Grupo.objects.create(nombre="Norte")
    GrupoMiembro.objects.create(grupo=grupo, persona=pastor.persona, rol="lider")
    pub = Publicacion.objects.create(autor=pastor, autor_nombre="Pastor", texto="Hola")
    Audiencia.objects.create(publicacion=pub, tipo="iglesia", ref_id=1, etiqueta="Toda la iglesia")
    Persona.objects.create(nombre="Contacto suelto")
    AuditEvent.objects.create(action="x")
    return qa


def correr(*args, **env):
    salida = io.StringIO()
    call_command("limpiar_qa", *args, stdout=salida)
    return salida.getvalue()


def test_sin_cuentas_solo_lista_candidatas_y_no_borra(datos):
    assert "Super Usuario QA" in correr()
    assert Publicacion.objects.count() == 1


def test_la_vista_previa_no_borra(datos):
    texto = correr("--conservar", "55 0000 0001")
    assert "Vista previa" in texto
    assert Grupo.objects.count() == 1 and User.objects.count() == 2


def test_ejecutar_exige_la_variable_de_entorno(datos, monkeypatch):
    monkeypatch.delenv("PERMITIR_LIMPIAR_QA", raising=False)
    with pytest.raises(CommandError):
        correr("--conservar", "55 0000 0001", "--ejecutar")
    assert Grupo.objects.count() == 1


def test_borra_los_registros_y_conserva_la_cuenta_y_los_catalogos(datos, monkeypatch):
    monkeypatch.setenv("PERMITIR_LIMPIAR_QA", "1")
    tipos = TipoOfrenda.objects.count()
    roles = Rol.objects.count()
    correr("--conservar", "55 0000 0001", "--incluir-bitacora", "--ejecutar")
    assert list(User.objects.values_list("whatsapp", flat=True)) == ["550000000" + "01"] or (
        User.objects.count() == 1 and User.objects.get().nombre == "Super Usuario QA"
    )
    assert Persona.objects.count() == 1 and Persona.objects.get().usuario == datos
    assert AsignacionRol.objects.filter(usuario=datos).count() == 1
    assert Grupo.objects.count() == 0 and GrupoMiembro.objects.count() == 0
    assert Publicacion.objects.count() == 0 and Audiencia.objects.count() == 0
    # Solo queda la huella de la propia limpieza y el bloqueo de la bitácora sigue activo
    assert list(AuditEvent.objects.values_list("action", flat=True)) == ["qa.limpieza"]
    with pytest.raises(Exception):  # noqa: B017
        with transaction.atomic(), connection.cursor() as cursor:
            cursor.execute("DELETE FROM core_auditevent")
    assert TipoOfrenda.objects.count() == tipos and Rol.objects.count() == roles


def test_sin_incluir_bitacora_no_borra(datos, monkeypatch):
    monkeypatch.setenv("PERMITIR_LIMPIAR_QA", "1")
    with pytest.raises(CommandError):
        correr("--conservar", "55 0000 0001", "--ejecutar")
    assert Grupo.objects.count() == 1


def test_cuenta_inexistente_se_rechaza(datos):
    with pytest.raises(CommandError):
        correr("--conservar", "55 9999 9999")
