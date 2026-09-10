from flask import render_template, request


def registrar_rutas_inicio(app, login_required, es_dispositivo_movil):
    """Registra la portada y la vista de diagnóstico de dispositivo."""

    @app.route("/")
    @login_required
    def inicio():
        if es_dispositivo_movil():
            return render_template("maquinaria_qr/index.html")
        return render_template("index.html")

    @app.route("/prueba")
    def prueba():
        user_agent = request.headers.get("User-Agent")
        dispositivo = (
            "CELULAR" if es_dispositivo_movil() else "COMPUTADORA"
        )
        return f"<h2>{user_agent}</h2><hr>{dispositivo}"
