"""Reglas compartidas para el avance de expedientes nacionales e importados."""
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
import unicodedata


CAMPOS_IMPORTACION = (
    ("factura", "Factura"),
    ("pedimento", "Pedimento"),
    ("entrada_mtz", "Entrada MTZ"),
    ("id_imp", "ID IMP"),
    ("inbond", "Inbond"),
    ("origen", "Origen"),
    ("fecha_importacion", "Fecha de Importación"),
    ("kg_bruto", "Kg Bruto"),
    ("total_bultos", "Total Bultos"),
    ("documentacion_completa", "Documentación Completa"),
)
CAMPOS_NACIONALES = tuple(
    campo for campo in CAMPOS_IMPORTACION
    if campo[0] in ("factura", "origen", "documentacion_completa")
)
SIN_DATO = {"", "-", "--", "PENDIENTE", "POR DEFINIR", "SIN DATO", "SIN DATOS",
            "SIN INFORMACION", "NULL", "NONE", "N/A", "NA", "NO APLICA"}


def normalizar(valor):
    texto = " ".join(str(valor if valor is not None else "").split()).upper()
    return "".join(c for c in unicodedata.normalize("NFD", texto)
                   if unicodedata.category(c) != "Mn")


def fecha_valida(valor):
    if isinstance(valor, (date, datetime)):
        return valor
    try:
        return date.fromisoformat(str(valor).strip())
    except (ValueError, TypeError):
        return None


def campo_completo(clave, valor):
    texto = normalizar(valor)
    if clave == "documentacion_completa":
        return texto == "SI"
    # NA es la convención existente para una factura que no aplica.
    if clave == "factura" and texto in {"NA", "N/A", "NO APLICA"}:
        return True
    if texto in SIN_DATO:
        return False
    if clave == "fecha_importacion":
        return fecha_valida(valor) is not None
    if clave in {"kg_bruto", "total_bultos"}:
        try:
            numero = Decimal(texto)
            return (numero.is_finite() and numero > 0
                    and (clave != "total_bultos" or numero == numero.to_integral_value()))
        except InvalidOperation:
            return False
    return True


def estado_expediente_aduanal(aduana):
    nacional = bool(aduana) and normalizar(aduana.get("origen")) == "NACIONAL"
    campos = CAMPOS_NACIONALES if nacional else CAMPOS_IMPORTACION
    detalle = []
    for clave, etiqueta in campos:
        valor = aduana.get(clave) if aduana else None
        completo = campo_completo(clave, valor)
        if clave == "fecha_importacion" and completo:
            mostrar = fecha_valida(valor).strftime("%d/%m/%Y")
        elif clave == "documentacion_completa":
            mostrar = "Completa" if completo else "Pendiente de confirmar"
        elif completo:
            mostrar = str(valor).strip()
        else:
            mostrar = "Pendiente"
        detalle.append({"clave": clave, "etiqueta": etiqueta,
                        "valor": mostrar, "completo": completo})
    faltantes = [campo["etiqueta"] for campo in detalle if not campo["completo"]]
    completos = len(campos) - len(faltantes)
    estado = "Sin expediente" if not aduana else ("Incompleto" if faltantes else "Completo")
    return {
        "porcentaje": round(completos / len(campos) * 100),
        "estado": estado,
        "color": {"Sin expediente": "danger", "Incompleto": "warning", "Completo": "success"}[estado],
        "completos": completos, "pendientes": len(faltantes),
        "total": len(campos), "faltantes": faltantes,
        "nacional": nacional, "campos": detalle,
    }

