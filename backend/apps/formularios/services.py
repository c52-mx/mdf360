"""Diseñador de formularios: campos adicionales para Persona y Grupo.

Modelo híbrido (CFG-06): las entidades siguen con sus columnas fijas y los campos que agrega el
diseñador se guardan en su `datos_extra`. Un campo nunca se borra, solo se desactiva (CFG-08), y los
de tipo «relación» guardan el id del registro al que apuntan (CFG-07).
"""

from datetime import date

from django.core.exceptions import ValidationError
from django.db import transaction

from apps.core import audit

from .models import Formulario

ENTIDADES = {"persona": "Personas", "grupo": "Grupos de Conexión"}
TIPOS = {
    "texto": "Texto corto",
    "textarea": "Texto largo",
    "numero": "Número",
    "fecha": "Fecha",
    "seleccion": "Lista de opciones",
    "casilla": "Casilla (sí o no)",
    "relacion": "Relación con otro registro",
}
OBJETIVOS = {"persona": "Persona", "grupo": "Grupo de Conexión", "ministerio": "Ministerio"}
LIMITE_CAMPOS = 40
LIMITE_TEXTO = 2000


def entidad_valida(entidad: str) -> bool:
    return entidad in ENTIDADES


def vigente(entidad: str) -> dict:
    f = Formulario.objects.filter(entidad=entidad).order_by("-version").first()
    return {"entidad": entidad, "version": f.version if f else 0, "campos": f.campos if f else []}


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
    objetivo = c.get("objetivo", "")
    if tipo == "relacion" and objetivo not in OBJETIVOS:
        raise ValidationError(f"El campo «{etiqueta}» necesita elegir a qué apunta.")
    return {
        "clave": clave,
        "etiqueta": etiqueta,
        "tipo": tipo,
        "ayuda": str(c.get("ayuda", "")).strip()[:200],
        "requerido": bool(c.get("requerido", False)),
        "activo": bool(c.get("activo", True)),
        "reportable": bool(c.get("reportable", False)),
        "opciones": opciones if tipo == "seleccion" else [],
        "objetivo": objetivo if tipo == "relacion" else "",
    }


@transaction.atomic
def guardar(entidad: str, campos, *, actor, request=None) -> dict:
    """Crea una versión nueva. Los campos existentes no se pueden quitar ni cambiar de tipo."""
    if not entidad_valida(entidad):
        raise ValidationError("Formulario no válido.")
    if not isinstance(campos, list) or len(campos) > LIMITE_CAMPOS:
        raise ValidationError(f"El formulario admite hasta {LIMITE_CAMPOS} campos.")
    nuevos = [_validar_campo(c) for c in campos]
    claves = [c["clave"] for c in nuevos]
    if len(set(claves)) != len(claves):
        raise ValidationError("Hay campos con la misma clave.")
    actual = vigente(entidad)
    por_clave = {c["clave"]: c for c in nuevos}
    for previo in actual["campos"]:
        nuevo = por_clave.get(previo["clave"])
        if nuevo is None:
            raise ValidationError(
                f"El campo «{previo['etiqueta']}» no se puede quitar; "
                "desactívalo para conservar sus respuestas."
            )
        if nuevo["tipo"] != previo["tipo"] or nuevo["objetivo"] != previo["objetivo"]:
            raise ValidationError(f"El tipo del campo «{previo['etiqueta']}» no se puede cambiar.")
    if nuevos == actual["campos"]:
        return actual
    f = Formulario.objects.create(
        entidad=entidad, version=actual["version"] + 1, campos=nuevos, creado_por=actor
    )
    audit.log(
        "formulario.guardado", actor=actor, request=request, entidad=entidad, version=f.version,
        campos=len(nuevos),
    )  # fmt: skip
    return {"entidad": entidad, "version": f.version, "campos": f.campos}


# ---------- respuestas ----------
def _modelo(objetivo: str):
    if objetivo == "persona":
        from apps.personas.models import Persona

        return Persona
    if objetivo == "grupo":
        from apps.grupos.models import Grupo

        return Grupo
    from apps.unidades.models import Unidad

    return Unidad


def _valor(campo: dict, valor):
    """Valida y normaliza un valor; None significa «vacío»."""
    tipo, etiqueta = campo["tipo"], campo["etiqueta"]
    if tipo == "casilla":
        return bool(valor)
    if valor in (None, ""):
        return None
    if tipo in ("texto", "textarea"):
        texto = str(valor).strip()
        if len(texto) > LIMITE_TEXTO:
            raise ValidationError(f"«{etiqueta}» es demasiado largo.")
        return texto or None
    if tipo == "numero":
        try:
            numero = float(str(valor).replace(",", "."))
        except ValueError as exc:
            raise ValidationError(f"«{etiqueta}» debe ser un número.") from exc
        return int(numero) if numero.is_integer() else numero
    if tipo == "fecha":
        try:
            return date.fromisoformat(str(valor)).isoformat()
        except ValueError as exc:
            raise ValidationError(f"«{etiqueta}» debe ser una fecha válida.") from exc
    if tipo == "seleccion":
        if valor not in campo["opciones"]:
            raise ValidationError(f"«{etiqueta}»: elige una de las opciones.")
        return valor
    try:  # relación
        pk = int(valor)
    except (TypeError, ValueError) as exc:
        raise ValidationError(f"«{etiqueta}»: elige un registro válido.") from exc
    if not _modelo(campo["objetivo"]).objects.filter(pk=pk).exists():
        raise ValidationError(f"«{etiqueta}»: el registro elegido no existe.")
    return pk


def aplicar(entidad: str, actual: dict | None, nuevos) -> dict:
    """Valida lo enviado contra el formulario vigente y lo mezcla con lo que ya había.

    Solo cambian los campos activos; las respuestas de campos desactivados se conservan tal cual.
    """
    if not isinstance(nuevos, dict):
        raise ValidationError("Los datos adicionales deben ser un objeto.")
    resultado = dict(actual or {})
    for campo in vigente(entidad)["campos"]:
        if not campo["activo"]:
            continue
        clave = campo["clave"]
        valor = _valor(campo, nuevos.get(clave))
        if campo["requerido"] and (valor is None or valor is False):
            raise ValidationError(f"«{campo['etiqueta']}» es obligatorio.")
        if valor is None:
            resultado.pop(clave, None)
        else:
            resultado[clave] = valor
    return resultado


def etiquetas(entidad: str, datos: dict | None) -> dict:
    """Nombre del registro al que apunta cada campo de relación (para mostrar, no solo el id)."""
    salida = {}
    for campo in vigente(entidad)["campos"]:
        valor = (datos or {}).get(campo["clave"])
        if campo["tipo"] == "relacion" and valor:
            objeto = _modelo(campo["objetivo"]).objects.filter(pk=valor).first()
            salida[campo["clave"]] = str(objeto) if objeto else "(ya no existe)"
    return salida


# ---------- reportes ----------
def _registros(entidad: str):
    if entidad == "persona":
        from apps.personas.models import Persona

        return Persona.objects.filter(activo=True)
    from apps.grupos.models import Grupo

    return Grupo.objects.filter(activo=True)


def _grupos_de_persona(pk: int) -> list[str]:
    from apps.grupos.models import GrupoMiembro

    miembros = GrupoMiembro.objects.filter(persona_id=pk, activo=True).select_related("grupo")
    return sorted({m.grupo.nombre for m in miembros})


def reporte(entidad: str) -> list[dict]:
    """Por cada campo reportable (activo o no): cuántos registros tienen cada respuesta.

    En campos de relación a una persona se cruza además con los grupos de esa persona.
    """
    campos = [c for c in vigente(entidad)["campos"] if c["reportable"]]
    registros = list(_registros(entidad))
    salida = []
    for campo in campos:
        conteo: dict[str, int] = {}
        por_grupo: dict[str, int] = {}
        for r in registros:
            valor = (r.datos_extra or {}).get(campo["clave"])
            if valor is None or valor == "":
                continue
            if campo["tipo"] == "relacion":
                etiqueta = etiquetas(entidad, r.datos_extra).get(campo["clave"], str(valor))
                if campo["objetivo"] == "persona":
                    for g in _grupos_de_persona(int(valor)) or ["Sin grupo"]:
                        por_grupo[g] = por_grupo.get(g, 0) + 1
            elif campo["tipo"] == "casilla":
                etiqueta = "Sí" if valor else "No"
            else:
                etiqueta = str(valor)
            conteo[etiqueta] = conteo.get(etiqueta, 0) + 1
        fila = {
            "clave": campo["clave"],
            "etiqueta": campo["etiqueta"],
            "activo": campo["activo"],
            "respuestas": sum(conteo.values()),
            "valores": [
                {"valor": v, "total": n} for v, n in sorted(conteo.items(), key=lambda x: -x[1])
            ],
        }
        if por_grupo:
            fila["por_grupo"] = [
                {"grupo": g, "total": n} for g, n in sorted(por_grupo.items(), key=lambda x: -x[1])
            ]
        salida.append(fila)
    return salida
