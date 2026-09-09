from flask import jsonify, render_template, session

from database.aduanas import obtener_aduanas
from database.dashboard import obtener_kpis_dashboard
from database.maquinarias import obtener_maquinarias
from models.auditoria_model import (
    obtener_actividad_filtrada,
    obtener_actividad_ultimos_7_dias,
)


def _datos_dashboard():
    maquinarias = obtener_maquinarias()
    aduanas = obtener_aduanas()

    total = len(maquinarias)
    bajas = (maquinarias["estado"] == "BAJA").sum()
    activos = (maquinarias["estado"] == "ACTIVO").sum()
    valor = maquinarias["valor_mx"].fillna(0).sum()
    origen = aduanas["origen"].fillna("SIN DATO").value_counts()
    documentacion = (
        aduanas["documentacion_completa"].fillna("NO").value_counts()
    )
    top = (
        maquinarias["categoria"]
        .fillna("SIN DATO")
        .value_counts()
        .head(10)
    )
    valor_origen = (
        aduanas.merge(
            maquinarias[["id_activo", "valor_mx"]],
            on="id_activo",
            how="left",
        )
        .groupby("origen")["valor_mx"]
        .sum()
    )

    return {
        "kpi": {
            "total": int(total),
            "activos": int(activos),
            "bajas": int(bajas),
            "valor": float(valor),
        },
        "origen": {
            "labels": origen.index.tolist(),
            "values": origen.values.tolist(),
        },
        "documentacion": {
            "labels": documentacion.index.tolist(),
            "values": documentacion.values.tolist(),
        },
        "top": {
            "labels": top.index.tolist(),
            "values": top.values.tolist(),
        },
        "valorOrigen": {
            "labels": valor_origen.index.tolist(),
            "values": valor_origen.values.tolist(),
        },
    }


def registrar_rutas_dashboard(app, login_required):
    """Registra los dashboards conservando URLs y endpoints existentes."""

    @app.route("/dashboard")
    @login_required
    def dashboard():
        return render_template("dashboard.html")

    @app.route("/dashboard/datos")
    @login_required
    def dashboard_datos():
        return jsonify(_datos_dashboard())

    @app.route("/m/dashboard")
    @login_required
    def dashboard_mobil():
        rol_actual = session.get("rol")
        nombre_actual = session.get("nombre")
        kpis = obtener_kpis_dashboard()
        actividad = obtener_actividad_filtrada(
            rol=rol_actual,
            usuario_actual=nombre_actual,
            limite=3,
        )
        grafica_actividad = obtener_actividad_ultimos_7_dias(
            rol=rol_actual,
            usuario_actual=nombre_actual,
        )

        return render_template(
            "maquinaria_qr/dashboard_mobil.html",
            **kpis,
            actividad=actividad,
            grafica_actividad=grafica_actividad,
        )
