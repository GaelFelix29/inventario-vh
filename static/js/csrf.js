(function () {
    "use strict";

    const meta = document.querySelector('meta[name="csrf-token"]');

    if (!meta || !meta.content) {
        return;
    }

    const token = meta.content;
    const metodosSeguros = new Set(["GET", "HEAD", "OPTIONS", "TRACE"]);

    function agregarTokenAFormularios() {
        document.querySelectorAll("form").forEach(function (formulario) {
            const metodo = (formulario.method || "GET").toUpperCase();

            if (metodosSeguros.has(metodo)) {
                return;
            }

            if (formulario.querySelector('input[name="csrf_token"]')) {
                return;
            }

            const campo = document.createElement("input");
            campo.type = "hidden";
            campo.name = "csrf_token";
            campo.value = token;
            formulario.appendChild(campo);
        });
    }

    agregarTokenAFormularios();

    const observador = new MutationObserver(agregarTokenAFormularios);
    observador.observe(document.documentElement, {
        childList: true,
        subtree: true,
    });

    const fetchOriginal = window.fetch.bind(window);

    window.fetch = function (recurso, opciones) {
        const configuracion = Object.assign({}, opciones || {});
        const metodo = (configuracion.method || "GET").toUpperCase();
        const destino = new URL(
            typeof recurso === "string" ? recurso : recurso.url,
            window.location.href
        );

        if (!metodosSeguros.has(metodo) && destino.origin === window.location.origin) {
            const encabezados = new Headers(configuracion.headers || {});
            encabezados.set("X-CSRFToken", token);
            configuracion.headers = encabezados;
        }

        return fetchOriginal(recurso, configuracion);
    };
})();
