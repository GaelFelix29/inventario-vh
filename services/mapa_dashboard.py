"""Resumen geográfico del inventario, sin geocodificación de nombres ambiguos."""
import hashlib
import math
import unicodedata


def normalizar_ubicacion(valor):
    if valor is None or (isinstance(valor, float) and math.isnan(valor)):
        return "SIN UBICACION"
    texto = " ".join(str(valor).split()).upper()
    texto = "".join(c for c in unicodedata.normalize("NFD", texto)
                    if unicodedata.category(c) != "Mn")
    return texto or "SIN UBICACION"


def resumir_mapa(registros, coordenadas):
    catalogo = {normalizar_ubicacion(k): v for k, v in coordenadas.items()}
    grupos = {}
    colores = ("#078854", "#2563eb", "#9333ea", "#d97706", "#dc3545", "#0891b2", "#be185d")
    for fila in registros:
        nombre = normalizar_ubicacion(fila.get("ubicacion"))
        if nombre not in grupos:
            indice = int(hashlib.sha256(nombre.encode()).hexdigest()[:8], 16) % len(colores)
            grupos[nombre] = {"nombre": nombre, "total": 0, "activos": 0, "bajas": 0,
                              "otros": 0, "color": colores[indice], "coordenadas": None}
        grupo = grupos[nombre]
        grupo["total"] += 1
        estado = str(fila.get("estado") or "").strip().upper()
        grupo["activos" if estado == "ACTIVO" else "bajas" if estado == "BAJA" else "otros"] += 1

    for nombre, grupo in grupos.items():
        dato = catalogo.get(nombre)
        if isinstance(dato, dict) and nombre != "SIN UBICACION":
            try:
                lat, lng = float(dato["lat"]), float(dato["lng"])
                if (math.isfinite(lat) and math.isfinite(lng)
                        and -90 <= lat <= 90 and -180 <= lng <= 180):
                    grupo["coordenadas"] = [lat, lng]
            except (KeyError, ValueError, TypeError):
                pass
    ubicaciones = sorted(grupos.values(), key=lambda g: (-g["total"], g["nombre"]))
    return {"ubicaciones": ubicaciones,
            "total": sum(g["total"] for g in ubicaciones),
            "localizadas": sum(g["coordenadas"] is not None for g in ubicaciones),
            "sin_localizar": sum(g["coordenadas"] is None for g in ubicaciones)}

