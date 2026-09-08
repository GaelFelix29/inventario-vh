document.addEventListener("DOMContentLoaded", function () {

    const formulario =
        document.getElementById("formEvidencia");

    const inputCamara =
        document.getElementById("inputCamara");

    const inputGaleria =
        document.getElementById("inputGaleria");

    const inputDocumentos =
        document.getElementById("inputDocumentos");

    const seccionSeleccion =
        document.getElementById("seccionSeleccion");

    const contenedorPreview =
        document.getElementById("contenedorPreview");

    const contadorSeleccion =
        document.getElementById("contadorSeleccion");

    const botonCancelar =
        document.getElementById("cancelarSeleccion");

    const botonGuardar =
        document.getElementById("guardarEvidencias");

    const textoGuardar =
        document.getElementById("textoGuardar");

    const MAXIMO_ARCHIVOS = 10;
    const TAMANIO_MAXIMO = 8 * 1024 * 1024;

    const TIPOS_PERMITIDOS = [
        "image/jpeg",
        "image/png",
        "image/webp"
    ];

    let archivosSeleccionados = [];
    let urlsTemporales = [];

    function claveArchivo(archivo) {

        return [
            archivo.name,
            archivo.size,
            archivo.lastModified
        ].join("-");

    }

    function liberarUrlsTemporales() {

        urlsTemporales.forEach(function (url) {
            URL.revokeObjectURL(url);
        });

        urlsTemporales = [];

    }

    function sincronizarInput() {

        const transferencia = new DataTransfer();

        archivosSeleccionados.forEach(function (archivo) {
            transferencia.items.add(archivo);
        });

        inputDocumentos.files =
            transferencia.files;

    }

    function actualizarContador() {

        contadorSeleccion.textContent =
            archivosSeleccionados.length +
            " / " +
            MAXIMO_ARCHIVOS;

        textoGuardar.textContent =
            archivosSeleccionados.length === 1
                ? "Guardar evidencia"
                : "Guardar " +
                  archivosSeleccionados.length +
                  " evidencias";

    }

    function eliminarArchivo(clave) {

        archivosSeleccionados =
            archivosSeleccionados.filter(
                function (archivo) {

                    return claveArchivo(archivo) !== clave;

                }
            );

        sincronizarInput();
        mostrarVistaPrevia();

    }

    function mostrarVistaPrevia() {

        liberarUrlsTemporales();

        contenedorPreview.replaceChildren();

        archivosSeleccionados.forEach(
            function (archivo) {

                const url =
                    URL.createObjectURL(archivo);

                urlsTemporales.push(url);

                const tarjeta =
                    document.createElement("article");

                tarjeta.className =
                    "evidencia-preview-card";

                const imagen =
                    document.createElement("img");

                imagen.src = url;
                imagen.alt = archivo.name;

                const informacion =
                    document.createElement("div");

                informacion.className =
                    "evidencia-preview-info";

                const nombre =
                    document.createElement("span");

                nombre.textContent =
                    archivo.name;

                const tamanio =
                    document.createElement("small");

                tamanio.textContent =
                    (
                        archivo.size /
                        1024 /
                        1024
                    ).toFixed(1) + " MB";

                informacion.append(
                    nombre,
                    tamanio
                );

                const botonEliminar =
                    document.createElement("button");

                botonEliminar.type = "button";

                botonEliminar.className =
                    "evidencia-preview-eliminar";

                botonEliminar.setAttribute(
                    "aria-label",
                    "Quitar " + archivo.name
                );

                const icono =
                    document.createElement("i");

                icono.className =
                    "bi bi-x-lg";

                botonEliminar.appendChild(icono);

                botonEliminar.addEventListener(
                    "click",
                    function () {

                        eliminarArchivo(
                            claveArchivo(archivo)
                        );

                    }
                );

                tarjeta.append(
                    imagen,
                    informacion,
                    botonEliminar
                );

                contenedorPreview.appendChild(
                    tarjeta
                );

            }
        );

        const hayArchivos =
            archivosSeleccionados.length > 0;

        seccionSeleccion.hidden =
            !hayArchivos;

        botonGuardar.disabled =
            !hayArchivos;

        actualizarContador();

    }

    function agregarArchivos(listaArchivos) {

        const nuevosArchivos =
            Array.from(listaArchivos);

        for (const archivo of nuevosArchivos) {

            if (
                !TIPOS_PERMITIDOS.includes(
                    archivo.type
                )
            ) {

                alert(
                    archivo.name +
                    " no es una imagen JPG, PNG o WEBP."
                );

                continue;

            }

            if (
                archivo.size >
                TAMANIO_MAXIMO
            ) {

                alert(
                    archivo.name +
                    " supera el límite de 8 MB."
                );

                continue;

            }

            const yaExiste =
                archivosSeleccionados.some(
                    function (existente) {

                        return (
                            claveArchivo(existente) ===
                            claveArchivo(archivo)
                        );

                    }
                );

            if (yaExiste) {
                continue;
            }

            if (
                archivosSeleccionados.length >=
                MAXIMO_ARCHIVOS
            ) {

                alert(
                    "Solo puede seleccionar un máximo " +
                    "de 10 imágenes."
                );

                break;

            }

            archivosSeleccionados.push(
                archivo
            );

        }

        sincronizarInput();
        mostrarVistaPrevia();

        inputCamara.value = "";
        inputGaleria.value = "";

    }

    inputCamara?.addEventListener(
        "change",
        function () {

            agregarArchivos(
                inputCamara.files
            );

        }
    );

    inputGaleria?.addEventListener(
        "change",
        function () {

            agregarArchivos(
                inputGaleria.files
            );

        }
    );

    botonCancelar?.addEventListener(
        "click",
        function () {

            archivosSeleccionados = [];

            sincronizarInput();
            mostrarVistaPrevia();

        }
    );

    formulario?.addEventListener(
        "submit",
        function (evento) {

            if (
                archivosSeleccionados.length === 0
            ) {

                evento.preventDefault();

                alert(
                    "Seleccione al menos una imagen."
                );

                return;

            }

            botonGuardar.disabled = true;

            textoGuardar.textContent =
                "Guardando evidencias...";

        }
    );

    window.addEventListener(
        "beforeunload",
        liberarUrlsTemporales
    );

});


// ==========================================
// VISOR DE EVIDENCIAS GUARDADAS
// ==========================================

let actual = 0;

function actualizar() {

    if (
        !Array.isArray(imagenes) ||
        imagenes.length === 0
    ) {
        return;
    }

    const imagenGrande =
        document.getElementById("imagenGrande");

    const contador =
        document.getElementById("contador");

    if (imagenGrande) {
        imagenGrande.src =
            imagenes[actual].url;
    }

    if (contador) {

        contador.textContent =
            `${actual + 1} / ${imagenes.length}`;

    }

}

function abrirVisor(indice) {

    actual = indice;

    actualizar();

    document.getElementById(
        "visor"
    )?.classList.add("mostrar");

    document.body.style.overflow =
        "hidden";

    const navegacion =
        document.querySelector(
            ".bottom-nav"
        );

    if (navegacion) {
        navegacion.classList.add("oculta");
    }

}

function cerrarVisor() {

    document.getElementById(
        "visor"
    )?.classList.remove("mostrar");

    document.body.style.overflow = "";

    const navegacion =
        document.querySelector(
            ".bottom-nav"
        );

    if (navegacion) {
        navegacion.classList.remove("oculta");
    }

}

function siguiente() {

    if (!imagenes.length) {
        return;
    }

    actual =
        (actual + 1) %
        imagenes.length;

    actualizar();

}

function anterior() {

    if (!imagenes.length) {
        return;
    }

    actual =
        (
            actual - 1 +
            imagenes.length
        ) %
        imagenes.length;

    actualizar();

}

function eliminarImagen() {

    if (
        !imagenes.length ||
        !confirm(
            "¿Eliminar esta evidencia?"
        )
    ) {
        return;
    }

    window.location.href =
        "/evidencias/" +
        encodeURIComponent(
            imagenes[actual].id
        ) +
        "/eliminar";

}

document.addEventListener(
    "keydown",
    function (evento) {

        const visor =
            document.getElementById("visor");

        if (
            !visor ||
            !visor.classList.contains("mostrar")
        ) {
            return;
        }

        if (evento.key === "Escape") {
            cerrarVisor();
        }

        if (evento.key === "ArrowRight") {
            siguiente();
        }

        if (evento.key === "ArrowLeft") {
            anterior();
        }

    }
);