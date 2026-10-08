ESTADOS_AGENDA = (
    ("PROGRAMADO", "Programado"),
    ("EN_PROCESO", "En proceso"),
    ("REALIZADO", "Realizado"),
    ("NO_REALIZADO", "No realizado"),
    ("REPROGRAMADO", "Reprogramado"),
)

POR_PAGINA_VALIDOS = (8, 12, 20)


def estado_visible(item):
    """Devuelve el estado que debe mostrarse en la agenda del equipo."""
    if item.get("estado_ejecucion") == "BORRADOR":
        return "EN_PROCESO"
    if item.get("estado_ejecucion") == "COMPLETO":
        return "REALIZADO"
    return item.get("estado") or "PROGRAMADO"


def preparar_agenda(agenda, semana=None, estado="", pagina=1, por_pagina=8):
    """Filtra y pagina una agenda sin modificar los registros originales."""
    semana = semana if isinstance(semana, int) and 1 <= semana <= 52 else None
    estados_validos = {clave for clave, _ in ESTADOS_AGENDA}
    estado = estado if estado in estados_validos else ""
    por_pagina = por_pagina if por_pagina in POR_PAGINA_VALIDOS else 8
    pagina = max(1, pagina if isinstance(pagina, int) else 1)

    registros = []
    for registro in agenda:
        item = dict(registro)
        item["estado_vista"] = estado_visible(item)
        registros.append(item)

    total_sin_filtro = len(registros)
    if semana is not None:
        registros = [item for item in registros if item.get("semana") == semana]
    if estado:
        registros = [item for item in registros if item["estado_vista"] == estado]

    total = len(registros)
    paginas = max(1, (total + por_pagina - 1) // por_pagina)
    pagina = min(pagina, paginas)
    inicio = (pagina - 1) * por_pagina

    return {
        "items": registros[inicio:inicio + por_pagina],
        "semana": semana,
        "estado": estado,
        "pagina": pagina,
        "paginas": paginas,
        "por_pagina": por_pagina,
        "total": total,
        "total_sin_filtro": total_sin_filtro,
    }
