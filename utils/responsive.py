from flask import render_template, request


def es_movil():

    user_agent = request.user_agent.string.lower()

    dispositivos = [

        "android",
        "iphone",
        "ipad",
        "mobile"

    ]

    return any(d in user_agent for d in dispositivos)


def render_responsive(
    mobile,
    desktop,
    **contexto
):

    if es_movil():

        return render_template(
            mobile,
            **contexto
        )

    return render_template(
        desktop,
        **contexto
    )