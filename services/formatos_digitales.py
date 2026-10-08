"""Carga y resuelve las plantillas digitales de mantenimiento preventivo."""

import json
from functools import lru_cache
from pathlib import Path


CATALOGO_DIGITAL = (
    Path(__file__).resolve().parent.parent
    / "config"
    / "formatos_mantenimiento_digitales.json"
)


@lru_cache(maxsize=1)
def cargar_catalogo_digital():
    with CATALOGO_DIGITAL.open(encoding="utf-8") as archivo:
        contenido = json.load(archivo)
    return contenido.get("formatos", {})


def obtener_plantilla_documento(codigo_documento, incluir_bloqueados=False):
    codigo = " ".join((codigo_documento or "").upper().split())
    plantilla = cargar_catalogo_digital().get(codigo)
    if not plantilla:
        return None
    if not incluir_bloqueados and not plantilla.get("habilitado", False):
        return None
    return plantilla


def obtener_plantilla_equipo(codigo_mantenimiento, incluir_bloqueados=False):
    codigo = " ".join((codigo_mantenimiento or "").upper().split())
    for plantilla in cargar_catalogo_digital().values():
        if plantilla.get("codigo_mantenimiento", "").upper() != codigo:
            continue
        if incluir_bloqueados or plantilla.get("habilitado", False):
            return plantilla
    return None


def obtener_plantilla_ejecucion(ejecucion):
    """Prefiere la copia histórica guardada al iniciar el mantenimiento."""
    if not ejecucion:
        return None
    snapshot = ejecucion.get("plantilla_json")
    if isinstance(snapshot, str):
        try:
            snapshot = json.loads(snapshot)
        except (TypeError, ValueError):
            snapshot = None
    if isinstance(snapshot, dict) and snapshot.get("secciones"):
        return snapshot
    plantilla = obtener_plantilla_documento(ejecucion.get("codigo_documento"))
    if plantilla:
        return plantilla
    return obtener_plantilla_equipo(ejecucion.get("formato") or ejecucion.get("codigo"))


def datos_plantilla_para_vista(plantilla):
    secciones = []
    for seccion in (plantilla or {}).get("secciones", []):
        actividades = [
            (actividad["clave"], actividad["texto"])
            for actividad in seccion.get("actividades", [])
        ]
        secciones.append((seccion.get("titulo", "Actividades"), actividades))
    return secciones, list((plantilla or {}).get("materiales", []))


def claves_plantilla(plantilla):
    return [
        actividad["clave"]
        for seccion in (plantilla or {}).get("secciones", [])
        for actividad in seccion.get("actividades", [])
    ]


def normalizar_procedimientos(valores, permitidos=None):
    """Normaliza selección múltiple y conserva el orden del formato oficial."""
    if isinstance(valores, str):
        valores = valores.split(",")
    entradas = [
        " ".join(str(valor).upper().split())
        for valor in (valores or [])
        if str(valor).strip()
    ]
    seleccionados = set(entradas)
    catalogo = [
        " ".join(str(valor).upper().split())
        for valor in (entradas if permitidos is None else permitidos)
        if str(valor).strip()
    ]
    return list(dict.fromkeys(
        valor for valor in catalogo if valor in seleccionados
    ))


def serializar_procedimientos(valores, permitidos=None):
    """Guarda una o varias opciones en la columna histórica existente."""
    return ",".join(normalizar_procedimientos(valores, permitidos))


def presentar_procedimientos(valor):
    procedimientos = normalizar_procedimientos(valor)
    if not procedimientos:
        return "-"
    etiquetas = [procedimiento.title() for procedimiento in procedimientos]
    if len(etiquetas) == 1:
        return etiquetas[0]
    return ", ".join(etiquetas[:-1]) + " y " + etiquetas[-1]


def serializar_plantilla(plantilla):
    return json.dumps(plantilla, ensure_ascii=False)
