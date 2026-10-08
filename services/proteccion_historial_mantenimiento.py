def mantenimiento_protegido(registro):
    """Un registro iniciado, documentado o realizado forma parte del historial."""
    return bool(
        registro
        and (
            registro.get("tiene_ejecucion")
            or registro.get("tiene_documentos")
            or registro.get("estado") == "REALIZADO"
        )
    )


def validar_cambio_mantenimiento(registro, nuevo_estado):
    """Evita borrar o cambiar un mantenimiento que ya contiene evidencia."""
    if not mantenimiento_protegido(registro):
        return
    if nuevo_estado is None:
        raise ValueError(
            "No se puede borrar esta semana porque ya tiene un formulario, "
            "documentos o un mantenimiento realizado. El historial quedó protegido."
        )
    if nuevo_estado != registro.get("estado"):
        raise ValueError(
            "No se puede cambiar el estado de esta semana porque ya contiene "
            "historial de mantenimiento. Consulta su registro para ver la evidencia."
        )
