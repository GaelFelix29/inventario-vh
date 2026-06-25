function buscar(){

    let codigo=document.getElementById("codigo").value.trim();

    if(codigo===""){

        return;

    }

    window.location="/"+codigo;

}

document.addEventListener("DOMContentLoaded",()=>{

    let caja=document.getElementById("codigo");

    if(caja){

        caja.focus();

        caja.addEventListener("keypress",(e)=>{

            if(e.key==="Enter"){

                buscar();

            }

        });

    }

});