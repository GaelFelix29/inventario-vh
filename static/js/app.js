//--------------------------------------------------
// BUSCAR MAQUINA
//--------------------------------------------------

function buscar() {

    const codigo = document.getElementById("codigo");

    if (!codigo) return;

    if (codigo.value.trim() === "") {
        alert("Ingrese un código.");
        return;
    }

    window.location.href = "/maquina/" + codigo.value.trim();

}

//======================================================
// CUANDO CARGA LA PÁGINA
//======================================================

document.addEventListener("DOMContentLoaded", () => {

    //--------------------------------------------------
    // BOTÓN VER CONTRASEÑA
    //--------------------------------------------------

    window.mostrarPassword = function () {

        const input = document.getElementById("password");
        const icono = document.getElementById("iconoPassword");

        if (!input || !icono) return;

        if (input.type === "password") {

            input.type = "text";

            icono.classList.remove("bi-eye");
            icono.classList.add("bi-eye-slash");

        } else {

            input.type = "password";

            icono.classList.remove("bi-eye-slash");
            icono.classList.add("bi-eye");

        }

    }

    //--------------------------------------------------
    // SI NO ESTAMOS EN ETIQUETAS SALIR
    //--------------------------------------------------

    const buscador = document.getElementById("buscar");

    if (!buscador) return;

    //--------------------------------------------------
    // VARIABLES
    //--------------------------------------------------

    const filtroEstado = document.getElementById("filtroEstado");
    const contador = document.getElementById("cantidadSeleccionados");

    const chkTodos = document.getElementById("chkSeleccionarTodo");

    const btnSeleccionarVisibles = document.getElementById("btnSeleccionarVisibles");
    const btnDeseleccionar = document.getElementById("btnDeseleccionar");

    const btnVista = document.getElementById("vistaPrevia");
    const btnImprimir = document.getElementById("imprimirQR");
    const btnPDF = document.getElementById("generarPDF");

    //--------------------------------------------------
    // CONTADOR
    //--------------------------------------------------

    function actualizarContador() {

        if (!contador) return;

        contador.textContent =
            document.querySelectorAll("tbody .seleccion:checked").length;

    }

    //--------------------------------------------------
    // FILTRO
    //--------------------------------------------------

    function filtrarTabla() {

        const texto = buscador.value.toLowerCase();
        const estado = filtroEstado.value;

        document.querySelectorAll(".filaQR").forEach(fila => {

            const contenido = fila.innerText.toLowerCase();
            const estadoFila = fila.cells[3].innerText.trim();

            let mostrar = true;

            if (texto !== "" && !contenido.includes(texto))
                mostrar = false;

            if (estado !== "Todos" && estadoFila !== estado)
                mostrar = false;

            fila.style.display = mostrar ? "" : "none";

        });

    }

    buscador.addEventListener("keyup", filtrarTabla);

    filtroEstado.addEventListener("change", filtrarTabla);

    //--------------------------------------------------
    // CHECKBOXES
    //--------------------------------------------------

    document.querySelectorAll(".seleccion").forEach(chk => {

        chk.addEventListener("change", actualizarContador);

    });

    //--------------------------------------------------
    // SELECCIONAR TODOS
    //--------------------------------------------------

    chkTodos.addEventListener("change", () => {

        document.querySelectorAll(".seleccion").forEach(chk => {

            chk.checked = chkTodos.checked;

        });

        actualizarContador();

    });

    //--------------------------------------------------
    // SELECCIONAR VISIBLES
    //--------------------------------------------------

    btnSeleccionarVisibles.addEventListener("click", () => {

        document.querySelectorAll(".filaQR").forEach(fila => {

            if (fila.style.display !== "none") {

                fila.querySelector(".seleccion").checked = true;

            }

        });

        actualizarContador();

    });

    //--------------------------------------------------
    // DESELECCIONAR
    //--------------------------------------------------

    btnDeseleccionar.addEventListener("click", () => {

        chkTodos.checked = false;

        document.querySelectorAll(".seleccion").forEach(chk => {

            chk.checked = false;

        });

        actualizarContador();

    });

    //--------------------------------------------------
    // OBTENER CÓDIGOS
    //--------------------------------------------------

    function obtenerSeleccionados() {

        let lista = [];

        document.querySelectorAll("tbody .seleccion:checked").forEach(chk => {

            lista.push(chk.value);

        });

        return lista;

    }

    //--------------------------------------------------
    // BOTONES
    //--------------------------------------------------

    btnVista.addEventListener("click", () => enviarEtiquetas(false));

    btnImprimir.addEventListener("click", () => enviarEtiquetas(true));

    btnPDF.addEventListener("click", () => enviarEtiquetas(true));

    //--------------------------------------------------
    // ENVIAR
    //--------------------------------------------------

    async function enviarEtiquetas() {

        const codigos = obtenerSeleccionados();

        if (codigos.length === 0) {

            alert("Selecciona al menos un activo.");

            return;

        }

        const datos = {

            codigos,

            copias: document.getElementById("copias").value,

            tamano: document.getElementById("tamano").value

        };

        try {

            const respuesta = await fetch("/etiquetas", {

                method: "POST",

                headers: {

                    "Content-Type": "application/json"

                },

                body: JSON.stringify(datos)

            });

            const html = await respuesta.text();

            const ventana = window.open("", "_blank");

            ventana.document.write(html);

            ventana.document.close();

        } catch (error) {

            alert(error.message);

        }

    }

    //--------------------------------------------------
    // ENTER
    //--------------------------------------------------

    buscador.addEventListener("keydown", e => {

        if (e.key === "Enter") {

            e.preventDefault();

            filtrarTabla();

        }

    });

    actualizarContador();

});