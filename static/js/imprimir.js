document.addEventListener("DOMContentLoaded", () => {

    const tabla = $("#tablaQR").DataTable();

    const btnVista = document.getElementById("vistaPrevia");
    const btnImprimir = document.getElementById("imprimirQR");
    const btnPDF = document.getElementById("generarPDF");

    const chkTodos = document.getElementById("chkSeleccionarTodo");

    const contador = document.getElementById("cantidadSeleccionados");

    const copias = document.getElementById("copias");

    const tamano = document.getElementById("tamano");

//--------------------------------------------------
// CONTADOR
//--------------------------------------------------

function actualizarContador() {

    let total = document.querySelectorAll(".seleccion:checked").length;

    if(contador){

        contador.textContent = total;

    }

}

//--------------------------------------------------
// SELECCIONAR TODOS
//--------------------------------------------------

if(chkTodos){

    chkTodos.addEventListener("change", () => {

        document.querySelectorAll(".seleccion").forEach(chk => {

            chk.checked = chkTodos.checked;

        });

        actualizarContador();

    });

}

//--------------------------------------------------
// CHECKBOXES
//--------------------------------------------------

document.querySelectorAll(".seleccion").forEach(chk => {

    chk.addEventListener("change", actualizarContador);

});

//--------------------------------------------------
// OBTENER SELECCIONADOS
//--------------------------------------------------

function obtenerSeleccionados(){

    let lista = [];

    document.querySelectorAll(".seleccion:checked").forEach(chk=>{

        lista.push(chk.value);

    });

    return lista;

}

//--------------------------------------------------
// ENVIAR ETIQUETAS
//--------------------------------------------------

async function enviarEtiquetas(imprimir = true){

    const codigos = obtenerSeleccionados();

    if(codigos.length === 0){

        alert("Selecciona al menos un activo.");

        return;

    }

    const datos = {

        codigos: codigos,

        copias: copias.value,

        tamano: tamano.value

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

        const ventana = window.open("", "_blank");

        if(!ventana){

            alert("El navegador bloqueó la ventana.");

            return;

        }

        ventana.document.open();
        ventana.document.write(html);
        ventana.document.close();

        if(imprimir){

            ventana.onload = function(){

                ventana.focus();
                ventana.print();

            };

        }

    }

    catch(error){

        console.error(error);

        alert(error);

    }

}

//--------------------------------------------------
// BOTONES
//--------------------------------------------------

if(btnVista){

    btnVista.addEventListener("click",()=>{

        enviarEtiquetas(false);

    });

}

if(btnImprimir){

    btnImprimir.addEventListener("click",()=>{

        enviarEtiquetas(true);

    });

}

if(btnPDF){

    btnPDF.addEventListener("click",()=>{

        enviarEtiquetas(true);

    });

}

//--------------------------------------------------
// CONTADOR INICIAL
//--------------------------------------------------

actualizarContador();

});

