from sqlalchemy import bindparam, text

from database.conexion import engine


DEPARTAMENTOS = {
    "ACT-0056": "Envasado de cápsulas",
    "ACT-0215": "Envasado de cápsulas",
    "ACT-0241": "Envasado de líquidos",
    "ACT-0242": "Envasado de líquidos",
    "ACT-0248": "Envasado de polvos",
    "ACT-0251": "Envasado de polvos",
    "ACT-0252": "Etiquetado",
    "ACT-0254": "Loteado",
    "ACT-0256": "Loteado",
    "ACT-0258": "Encapsulado",
    "ACT-0261": "Etiquetado",
    "ACT-0269": "Sellado",
    "ACT-0270": "Sellado",
    "ACT-0271": "Sellado",
    "ACT-0272": "Sellado",
    "ACT-0273": "Sellado",
    "ACT-0274": "Sellado",
}


def cargar_departamentos():
    """Carga departamentos solo en activos existentes que aún no tienen uno."""
    ids = list(DEPARTAMENTOS)
    consulta = text(
        "SELECT id_activo FROM maquinarias WHERE id_activo IN :ids"
    ).bindparams(bindparam("ids", expanding=True))

    with engine.begin() as conn:
        existentes = set(conn.execute(consulta, {"ids": ids}).scalars())
        faltantes = sorted(set(ids) - existentes)
        if faltantes:
            raise RuntimeError(
                "No se realizó ningún cambio. Faltan activos: "
                + ", ".join(faltantes)
            )

        actualizados = 0
        for id_activo, departamento in DEPARTAMENTOS.items():
            resultado = conn.execute(text("""
                UPDATE maquinarias
                SET departamento = :departamento
                WHERE id_activo = :id_activo
                  AND departamento IS NULL
            """), {
                "id_activo": id_activo,
                "departamento": departamento,
            })
            actualizados += resultado.rowcount

        print(f"Departamentos actualizados: {actualizados}")


if __name__ == "__main__":
    cargar_departamentos()
