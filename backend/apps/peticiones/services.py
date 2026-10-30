from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.accounts.permissions import tiene_permiso
from apps.core import audit, config

from . import crypto, registry
from .models import FormularioPeticion, Peticion

TIPOS = {"texto", "textarea", "seleccion", "casilla"}
LIMITE_TEXTO = 2000
LIMITE_CAMPOS = 30


class OrigenDesconocido(Exception):
    pass


class SinPermiso(Exception):
    pass


# ---------- formulario ----------
def formulario_vigente() -> FormularioPeticion:
    return FormularioPeticion.objects.order_by("-version").first()


def _validar_campo(c) -> dict:
    if not isinstance(c, dict):
        raise ValidationError("Cada campo debe ser un objeto.")
    clave = str(c.get("clave", "")).strip()
    etiqueta = str(c.get("etiqueta", "")).strip()
    tipo = c.get("tipo")
    if not clave or not clave.replace("_", "").isalnum() or len(clave) > 40:
        raise ValidationError("La clave de un campo solo admite letras, números y guion bajo.")
    if not etiqueta or len(etiqueta) > 120:
        raise ValidationError("Cada campo necesita una etiqueta (máximo 120 caracteres).")
    if tipo not in TIPOS:
        raise ValidationError("Tipo de campo no válido.")
    opciones = [str(o).strip() for o in c.get("opciones", []) if str(o).strip()]
    if tipo == "seleccion" and len(opciones) < 2:
        raise ValidationError(f"El campo «{etiqueta}» necesita al menos dos opciones.")
    return {
        "clave": clave,
        "etiqueta": etiqueta,
        "tipo": tipo,
        "identifica": bool(c.get("identifica", False)),
        "requerido": bool(c.get("requerido", False)),
        "activo": bool(c.get("activo", True)),
        "opciones": opciones if tipo == "seleccion" else [],
    }


@transaction.atomic
def guardar_formulario(campos, *, actor, request=None) -> FormularioPeticion:
    """Crea una versión nueva. Los campos existentes no se pueden quitar, solo desactivar."""
    if not isinstance(campos, list) or not campos or len(campos) > LIMITE_CAMPOS:
        raise ValidationError(f"El formulario debe tener entre 1 y {LIMITE_CAMPOS} campos.")
    nuevos = [_validar_campo(c) for c in campos]
    claves = [c["clave"] for c in nuevos]
    if len(set(claves)) != len(claves):
        raise ValidationError("Hay campos con la misma clave.")
    vigente = formulario_vigente()
    faltan = {c["clave"] for c in vigente.campos} - set(claves)
    if faltan:
        raise ValidationError(
            "Los campos existentes no se pueden quitar, solo desactivar: "
            + ", ".join(sorted(faltan))
        )
    if not any(c["activo"] for c in nuevos):
        raise ValidationError("Debe haber al menos un campo activo.")
    if not any(c["activo"] and c["requerido"] for c in nuevos):
        raise ValidationError(
            "Debe haber al menos un campo activo y obligatorio (el texto de la petición)."
        )
    version = FormularioPeticion.objects.create(
        version=vigente.version + 1, campos=nuevos, creado_por=actor
    )
    audit.log(
        "peticiones.formulario_cambiado", actor=actor, target=version, request=request,
        version=version.version, campos=len(nuevos),
    )  # fmt: skip
    return version


def _validar_datos(datos, formulario: FormularioPeticion) -> dict:
    if not isinstance(datos, dict):
        raise ValidationError("Los datos de la petición no son válidos.")
    activos = {c["clave"]: c for c in formulario.campos if c["activo"]}
    desconocidos = set(datos) - set(activos)
    if desconocidos:
        raise ValidationError("Hay campos que no existen en el formulario.")
    limpio = {}
    for clave, campo in activos.items():
        valor = datos.get(clave)
        if campo["tipo"] == "casilla":
            valor = bool(valor)
        else:
            valor = "" if valor is None else str(valor).strip()
            if len(valor) > LIMITE_TEXTO:
                raise ValidationError(f"«{campo['etiqueta']}» es demasiado largo.")
            if campo["tipo"] == "seleccion" and valor and valor not in campo["opciones"]:
                raise ValidationError(f"«{campo['etiqueta']}»: opción no válida.")
        if campo["requerido"] and (valor in ("", False)):
            raise ValidationError(f"«{campo['etiqueta']}» es obligatorio.")
        limpio[clave] = valor
    return limpio


# ---------- peticiones ----------
def purgar_vencidas(*, actor=None) -> int:
    """Borra definitivamente las peticiones cuyo plazo de conservación terminó."""
    vencidas = Peticion.objects.filter(expira_en__lte=timezone.now())
    total = vencidas.count()
    if total:
        vencidas.delete()
        audit.log("peticion.purgadas", actor=actor, cantidad=total)
    return total


@transaction.atomic
def registrar_peticion(
    *,
    origen_tipo,
    origen_id,
    referencia_id=None,
    datos,
    actor,
    request=None,
    visibilidad=None,
    ocultar_nombre=False,
) -> Peticion:
    origen = registry.obtener(origen_tipo)
    if origen is None:
        raise OrigenDesconocido
    if not origen.puede_registrar(actor, origen_id):
        raise SinPermiso
    etiqueta = origen.etiqueta(origen_id, referencia_id)
    if etiqueta is None:
        raise ValidationError("El origen de la petición no existe.")
    visibilidad = visibilidad or config.obtener("peticiones.visibilidad_por_defecto")
    if visibilidad not in Peticion.Visibilidad.values:
        raise ValidationError("Alcance no válido.")
    formulario = formulario_vigente()
    limpio = _validar_datos(datos, formulario)
    dias = int(config.obtener("peticiones.dias_retencion"))
    peticion = Peticion.objects.create(
        origen_tipo=origen_tipo,
        origen_id=origen_id,
        origen_etiqueta=etiqueta,
        referencia_id=referencia_id,
        formulario_version=formulario.version,
        datos_cifrados=crypto.cifrar(limpio),
        visibilidad=visibilidad,
        ocultar_nombre=bool(ocultar_nombre) and visibilidad != Peticion.Visibilidad.LIDERES,
        creada_por=actor,
        expira_en=Peticion.calcular_expiracion(dias),
    )
    audit.log(
        "peticion.creada", actor=actor, target=peticion, request=request,
        origen=origen_tipo, origen_id=origen_id, visibilidad=visibilidad,
        ocultar_nombre=peticion.ocultar_nombre,
    )  # fmt: skip
    return peticion


def _acceso(user, peticion: Peticion) -> str | None:
    origen = registry.obtener(peticion.origen_tipo)
    return origen.acceso(user, peticion.origen_id) if origen else None


def peticiones_visibles(user):
    """Peticiones que `user` puede leer.

    - Quien tiene acceso de líder a un origen ve todas las de ese origen.
    - Quien pertenece al origen ve las de alcance «grupo» y «equipo» si el origen lo permite.
    - Quien tiene el rol de Equipo de oración ve las de alcance «equipo» de cualquier origen.
    - Quien la registró la sigue viendo, salvo en «solo líderes» (ahí quien registra no lee).
    """
    from django.db.models import Q

    V = Peticion.Visibilidad
    condicion = Q(pk__in=[])
    if getattr(user, "pk", None):
        condicion |= Q(creada_por=user) & ~Q(visibilidad=V.LIDERES)
    for origen in registry.todos():
        niveles = origen.ids_por_acceso(user)
        lider = niveles.get(registry.LIDER)
        if lider is None:
            condicion |= Q(origen_tipo=origen.tipo)
        elif lider:
            condicion |= Q(origen_tipo=origen.tipo, origen_id__in=lider)
        miembro = niveles.get(registry.MIEMBRO) or []
        if miembro:
            condicion |= Q(
                origen_tipo=origen.tipo,
                origen_id__in=miembro,
                visibilidad__in=[V.GRUPO, V.EQUIPO],
            )
    if tiene_permiso(user, "peticiones.equipo_oracion"):
        condicion |= Q(visibilidad=V.EQUIPO)
    return Peticion.objects.filter(condicion)


def puede_ver(user, peticion: Peticion) -> bool:
    V = Peticion.Visibilidad
    nivel = _acceso(user, peticion)
    if nivel == registry.LIDER:
        return True
    if peticion.visibilidad == V.LIDERES:
        return False
    if peticion.creada_por_id is not None and peticion.creada_por_id == getattr(user, "pk", None):
        return True
    if nivel == registry.MIEMBRO:
        return True
    return peticion.visibilidad == V.EQUIPO and tiene_permiso(user, "peticiones.equipo_oracion")


def puede_gestionar(user, peticion: Peticion) -> bool:
    """Marcar como atendida o reactivar: solo líder del origen o superiores."""
    return _acceso(user, peticion) == registry.LIDER


def _claves_que_identifican(version: int) -> set[str]:
    formulario = FormularioPeticion.objects.filter(version=version).first()
    return {c["clave"] for c in (formulario.campos if formulario else []) if c.get("identifica")}


def cambiar_estado(peticion: Peticion, estado: str, *, actor, request=None) -> Peticion:
    if estado not in Peticion.Estado.values:
        raise ValidationError("Estado no válido.")
    peticion.estado = estado
    peticion.atendida_en = timezone.now() if estado == Peticion.Estado.ATENDIDA else None
    peticion.atendida_por = actor if estado == Peticion.Estado.ATENDIDA else None
    peticion.save(update_fields=["estado", "atendida_en", "atendida_por"])
    audit.log("peticion.estado", actor=actor, target=peticion, request=request, estado=estado)
    return peticion


def peticion_dict(p: Peticion, *, con_contenido: bool, viewer=None) -> dict:
    origen = registry.obtener(p.origen_tipo)
    base = {
        "id": p.pk,
        "origen": {
            "tipo": p.origen_tipo,
            "tipo_display": origen.nombre if origen else p.origen_tipo,
            "id": p.origen_id,
            "etiqueta": p.origen_etiqueta,
            "referencia_id": p.referencia_id,
        },
        "estado": p.estado,
        "estado_display": p.get_estado_display(),
        "visibilidad": p.visibilidad,
        "visibilidad_display": p.get_visibilidad_display(),
        "ocultar_nombre": p.ocultar_nombre,
        "creada_en": p.creada_en.isoformat(),
        "expira_en": p.expira_en.isoformat(),
    }
    if viewer is not None:
        base["puede_gestionar"] = puede_gestionar(viewer, p)
    if con_contenido:
        datos = crypto.descifrar(p.datos_cifrados)
        # Alcance amplio con nombre oculto: solo líderes y quien la registró ven quién la pide
        es_lider = viewer is not None and _acceso(viewer, p) == registry.LIDER
        es_autor = viewer is not None and p.creada_por_id == getattr(viewer, "pk", None)
        if p.ocultar_nombre and not (es_lider or es_autor):
            for clave in _claves_que_identifican(p.formulario_version):
                datos.pop(clave, None)
        base["datos"] = datos
        base["formulario_version"] = p.formulario_version
    return base
