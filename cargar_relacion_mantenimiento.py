from sqlalchemy import bindparam, text

from database.conexion import engine


RELACION = [
    {"id": "ACT-0056", "codigo": "CC-8", "nombre": "Contadora de cápsulas #8", "voltaje": "220 V"},
    {"id": "ACT-0215", "codigo": "CC-7", "nombre": "Contadora de cápsulas #7", "voltaje": "220 V"},
    {"id": "ACT-0241", "codigo": "MM-2", "nombre": "Marmita mezcladora #2", "voltaje": "220 V"},
    {"id": "ACT-0242", "codigo": "L4B-2", "nombre": "Llenadora de líquidos de 4 bocas #2", "voltaje": "220 V"},
    {"id": "ACT-0248", "codigo": "EPS-11", "nombre": "Envasadora de polvos semiautomática #11", "voltaje": "220 V"},
    {"id": "ACT-0251", "codigo": "EPS-12", "nombre": "Envasadora de polvos semiautomática #12", "voltaje": "220 V"},
    {"id": "ACT-0252", "codigo": "TC-1", "nombre": "Túnel de calor #1", "voltaje": "220 V"},
    {"id": "ACT-0254", "codigo": "LBA-3", "nombre": "Loteadora de banda automática #3", "voltaje": "220 V"},
    {"id": "ACT-0256", "codigo": "LBA-6", "nombre": "Loteadora de banda automática #6", "voltaje": "220 V"},
    {"id": "ACT-0258", "codigo": "ECO-7", "nombre": "Encapsuladora automática #7", "voltaje": "220 V 3PH"},
    {"id": "ACT-0261", "codigo": "TC-2", "nombre": "Túnel de calor #2", "voltaje": "220 V"},
    {"id": "ACT-0269", "codigo": "TRM-22", "nombre": "Termoselladora #22", "voltaje": "110 V"},
    {"id": "ACT-0270", "codigo": "TRM-19", "nombre": "Termoselladora #19", "voltaje": "110 V"},
    {"id": "ACT-0271", "codigo": "TRM-2", "nombre": "Termoselladora #2", "voltaje": "110 V"},
    {"id": "ACT-0272", "codigo": "TRM-17", "nombre": "Termoselladora #17", "voltaje": "110 V"},
    {"id": "ACT-0273", "codigo": "TRM-20", "nombre": "Termoselladora #20", "voltaje": "110 V"},
    {"id": "ACT-0274", "codigo": "TRM-18", "nombre": "Termoselladora #18", "voltaje": "110 V"},
]


def cargar_relacion():
    """Carga la relación completa o revierte todo si falta algún activo."""
    ids = [fila["id"] for fila in RELACION]
    consulta = text("SELECT id_activo FROM maquinarias WHERE id_activo IN :ids").bindparams(
        bindparam("ids", expanding=True)
    )
    with engine.begin() as conn:
        existentes = set(conn.execute(consulta, {"ids": ids}).scalars())
        faltantes = sorted(set(ids) - existentes)
        if faltantes:
            raise RuntimeError(
                "No se aplicó ningún cambio. Confirme estos códigos Vital: "
                + ", ".join(faltantes)
            )
        conn.execute(text("""
            UPDATE maquinarias
            SET codigo_mantenimiento = :codigo,
                nombre_mantenimiento = :nombre,
                voltaje = :voltaje
            WHERE id_activo = :id
        """), RELACION)
        print(f"Relación cargada correctamente: {len(RELACION)} activos.")


if __name__ == "__main__":
    cargar_relacion()
