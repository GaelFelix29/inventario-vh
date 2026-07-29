const input = document.getElementById("inputImagen");
const form = document.getElementById("formEvidencia");

if (input) {

    input.addEventListener("change", () => {

        if (input.files.length) {

            form.submit();

        }

    });

}

let actual = 0;

function actualizar() {

    document.getElementById("imagenGrande").src = imagenes[actual].url;

    document.getElementById("contador").textContent =
        `${actual + 1} / ${imagenes.length}`;

}

function abrirVisor(i) {

    actual = i;

    actualizar();

    document.getElementById("visor").classList.add("mostrar");

    const nav = document.querySelector(".bottom-nav");

    if (nav) {

        nav.classList.add("oculta");

    }

}

function cerrarVisor() {

    document.getElementById("visor").classList.remove("mostrar");

    const nav = document.querySelector(".bottom-nav");

    if (nav) {

        nav.classList.remove("oculta");

    }

}

function siguiente() {

    actual++;

    if (actual >= imagenes.length) {

        actual = 0;

    }

    actualizar();

}

function anterior() {

    actual--;

    if (actual < 0) {

        actual = imagenes.length - 1;

    }

    actualizar();

}

function eliminarImagen() {

    if (!confirm("¿Eliminar esta evidencia?")) {

        return;

    }

    window.location.href =
        "/evidencias/" +
        imagenes[actual].id +
        "/eliminar";

}