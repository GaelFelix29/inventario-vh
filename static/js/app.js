//======================================================
// IMPRESIÓN DE ETIQUETAS QR
//======================================================

document.addEventListener("DOMContentLoaded", () => {

    const buscador = document.getElementById("buscar");
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

    function actualizarContador(){

        let total=document.querySelectorAll("tbody .seleccion:checked").length;

        contador.textContent=total;

    }

    //--------------------------------------------------
    // FILTRAR
    //--------------------------------------------------

    function filtrarTabla(){

        let texto=buscador.value.toLowerCase();

        let estado=filtroEstado.value;

        document.querySelectorAll(".filaQR").forEach(fila=>{

            let contenido=fila.innerText.toLowerCase();

            let estadoFila=fila.cells[3].innerText.trim();

            let mostrar=true;

            if(texto!="" && !contenido.includes(texto)){

                mostrar=false;

            }

            if(estado!="Todos" && estadoFila!=estado){

                mostrar=false;

            }

            fila.style.display=mostrar ? "" : "none";

        });

    }

    buscador.addEventListener("keyup",filtrarTabla);

    filtroEstado.addEventListener("change",filtrarTabla);

    //--------------------------------------------------
    // CHECKBOXS
    //--------------------------------------------------

    document.querySelectorAll(".seleccion").forEach(chk=>{

        chk.addEventListener("change",()=>{

            actualizarContador();

        });

    });

    //--------------------------------------------------
    // SELECCIONAR TODOS
    //--------------------------------------------------

    chkTodos.addEventListener("change",()=>{

        document.querySelectorAll(".seleccion").forEach(chk=>{

            chk.checked=chkTodos.checked;

        });

        actualizarContador();

    });

    //--------------------------------------------------
    // SELECCIONAR VISIBLES
    //--------------------------------------------------

    btnSeleccionarVisibles.addEventListener("click",()=>{

        document.querySelectorAll(".filaQR").forEach(fila=>{

            if(fila.style.display!="none"){

                fila.querySelector(".seleccion").checked=true;

            }

        });

        actualizarContador();

    });

    //--------------------------------------------------
    // DESELECCIONAR TODOS
    //--------------------------------------------------

    btnDeseleccionar.addEventListener("click",()=>{

        chkTodos.checked=false;

        document.querySelectorAll(".seleccion").forEach(chk=>{

            chk.checked=false;

        });

        actualizarContador();

    });

    //--------------------------------------------------
    // OBTENER CÓDIGOS
    //--------------------------------------------------

    function obtenerSeleccionados(){

        let lista=[];

        document.querySelectorAll("tbody .seleccion:checked").forEach(chk=>{

            lista.push(chk.value);

        });

        return lista;

    }


        //--------------------------------------------------
    // VISTA PREVIA
    //--------------------------------------------------

    btnVista.addEventListener("click", () => {

        enviarEtiquetas(false);

    });

    //--------------------------------------------------
    // IMPRIMIR
    //--------------------------------------------------

    btnImprimir.addEventListener("click", () => {

        enviarEtiquetas(true);

    });

    //--------------------------------------------------
    // PDF
    //--------------------------------------------------

    btnPDF.addEventListener("click", () => {

        enviarEtiquetas(true);

    });

    //--------------------------------------------------
    // ENVIAR AL SERVIDOR
    //--------------------------------------------------

    async function enviarEtiquetas(imprimir = true){

        const codigos = obtenerSeleccionados();

        if(codigos.length===0){

            alert("Selecciona al menos un activo.");

            return;

        }

        const datos = {

            codigos: codigos,

            copias: document.getElementById("copias").value,

            tamano: document.getElementById("tamano").value

        };

        try{

            const respuesta = await fetch("/etiquetas",{

                method:"POST",

                headers:{

                    "Content-Type":"application/json"

                },

                body:JSON.stringify(datos)

            });

            if(!respuesta.ok){

                throw new Error(await respuesta.text());

            }

            const html = await respuesta.text();

            const ventana = window.open("","_blank");

            if(!ventana){

                alert("El navegador bloqueó la ventana.");

                return;

            }

            ventana.document.open();

            ventana.document.write(html);

            ventana.document.close();

        }

        catch(error){

            console.error(error);

            alert(error.message);

        }

    }

    //--------------------------------------------------
    // ENTER EN BUSCADOR
    //--------------------------------------------------

    buscador.addEventListener("keydown",(e)=>{

        if(e.key==="Enter"){

            e.preventDefault();

            filtrarTabla();

        }

    });

    //--------------------------------------------------
    // CONTADOR INICIAL
    //--------------------------------------------------

    actualizarContador();

});