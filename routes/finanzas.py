import math

from flask import abort, flash, redirect, render_template, request, session, url_for

from database.estados_cuenta import (importar_estado_cuenta, listar_estados_cuenta,
                                      listar_movimientos, obtener_estado_cuenta)
from services.importador_estados_cuenta import leer_estado_cuenta


ROLES_FINANCIEROS = ("Administrador", "Compras", "Finanzas")


def registrar_rutas_finanzas(app, login_required, roles_required, registrar_movimiento):
    @app.route("/finanzas/estados-cuenta")
    @login_required
    @roles_required(*ROLES_FINANCIEROS)
    def estados_cuenta():
        return render_template("finanzas/estados_cuenta.html", estados=listar_estados_cuenta())

    @app.route("/finanzas/estados-cuenta/importar", methods=["POST"])
    @login_required
    @roles_required("Administrador", "Finanzas")
    def importar_estado_cuenta_route():
        archivo = request.files.get("archivo")
        if not archivo or not archivo.filename.lower().endswith(".xlsx"):
            flash("Selecciona un archivo de Excel .xlsx.", "warning")
            return redirect(url_for("estados_cuenta"))
        try:
            estado = leer_estado_cuenta(archivo.stream, archivo.filename)
            estado_id = importar_estado_cuenta(estado, session["usuario_id"])
            registrar_movimiento(session["nombre"], f"Importó el estado de cuenta {archivo.filename}", "Finanzas", str(estado_id))
            flash(f"Estado importado: {len(estado['movimientos']):,} movimientos conciliados.", "success")
            return redirect(url_for("detalle_estado_cuenta", estado_id=estado_id))
        except ValueError as error:
            flash(str(error), "warning")
        except Exception as error:
            print("ERROR IMPORTANDO ESTADO DE CUENTA:", error)
            flash("No fue posible importar el archivo. Verifica que la migración esté aplicada.", "danger")
        return redirect(url_for("estados_cuenta"))

    @app.route("/finanzas/estados-cuenta/<int:estado_id>")
    @login_required
    @roles_required(*ROLES_FINANCIEROS)
    def detalle_estado_cuenta(estado_id):
        estado = obtener_estado_cuenta(estado_id)
        if not estado:
            abort(404)
        buscar = (request.args.get("buscar") or "").strip()
        tipo = request.args.get("tipo") or "todos"
        if tipo not in ("todos", "cargos", "abonos"):
            tipo = "todos"
        try:
            pagina = max(1, int(request.args.get("pagina") or 1))
        except ValueError:
            pagina = 1
        try:
            por_pagina = int(request.args.get("por_pagina") or 20)
        except ValueError:
            por_pagina = 20
        if por_pagina not in (10, 20, 50, 100):
            por_pagina = 20
        movimientos, total = listar_movimientos(
            estado_id, buscar, tipo, pagina, por_pagina
        )
        paginas = max(1, math.ceil(total / por_pagina))
        if pagina > paginas:
            pagina = paginas
            movimientos, total = listar_movimientos(
                estado_id, buscar, tipo, pagina, por_pagina
            )
        desde = ((pagina - 1) * por_pagina + 1) if total else 0
        hasta = min(pagina * por_pagina, total)
        return render_template("finanzas/detalle_estado_cuenta.html", estado=estado,
                               movimientos=movimientos, total=total, pagina=pagina,
                               paginas=paginas, por_pagina=por_pagina,
                               desde=desde, hasta=hasta, buscar=buscar, tipo=tipo)
