document.addEventListener("DOMContentLoaded", async () => {

    const respuesta = await fetch("/dashboard/datos");

    const datos = await respuesta.json();

    // ==============================
    // TARJETAS
    // ==============================

    document.getElementById("totalActivos").textContent =
        datos.kpi.total.toLocaleString();

    document.getElementById("activos").textContent =
        datos.kpi.activos.toLocaleString();

    document.getElementById("bajas").textContent =
        datos.kpi.bajas.toLocaleString();

    document.getElementById("valor").textContent =
        "$ " + datos.kpi.valor.toLocaleString();

    // ==============================
    // ORIGEN
    // ==============================

    new Chart(
        document.getElementById("graficaOrigen"),
        {

            type:"pie",

            data:{

                labels:datos.origen.labels,

                datasets:[{

                    data:datos.origen.values,

                    backgroundColor:[
                        "#198754",
                        "#0dcaf0",
                        "#ffc107",
                        "#dc3545",
                        "#6f42c1",
                        "#fd7e14",
                        "#20c997"
                    ]

                }]

            },

            options:{

                responsive:true,

                plugins:{

                    legend:{

                        position:"bottom"

                    }

                }

            }

        }

    );

    // ==============================
    // DOCUMENTACION
    // ==============================

    new Chart(
        document.getElementById("graficaEstado"),
        {

            type:"bar",

            data:{

                labels:datos.documentacion.labels,

                datasets:[{

                    label:"Documentación",

                    data:datos.documentacion.values,

                    backgroundColor:"#198754"

                }]

            },

            options:{

                responsive:true,

                plugins:{

                    legend:{

                        display:false

                    }

                }

            }

        }

    );

        // ==============================
    // TOP 10 MAQUINARIAS
    // ==============================

    new Chart(
        document.getElementById("graficaTop"),
        {

            type:"bar",

            data:{

                labels:datos.top.labels,

                datasets:[{

                    label:"Cantidad",

                    data:datos.top.values,

                    backgroundColor:"#0d6efd",

                    borderRadius:8

                }]

            },

            options:{

                indexAxis:"y",

                responsive:true,

                plugins:{

                    legend:{
                        display:false
                    }

                },

                scales:{

                    x:{
                        beginAtZero:true
                    }

                }

            }

        }

    );

    // ==============================
    // VALOR POR ORIGEN
    // ==============================

    new Chart(
        document.getElementById("graficaValorOrigen"),
        {

            type:"doughnut",

            data:{

                labels:datos.valorOrigen.labels,

                datasets:[{

                    data:datos.valorOrigen.values,

                    backgroundColor:[

                        "#198754",
                        "#0dcaf0",
                        "#ffc107",
                        "#dc3545",
                        "#6f42c1",
                        "#fd7e14",
                        "#20c997",
                        "#6610f2"

                    ]

                }]

            },

            options:{

                responsive:true,

                plugins:{

                    legend:{

                        position:"bottom"

                    }

                }

            }

        }

    );

    // ==============================
// TABLA RESUMEN
// ==============================

document.getElementById("tblTotal").textContent =
    datos.kpi.total.toLocaleString();

document.getElementById("tblActivos").textContent =
    datos.kpi.activos.toLocaleString();

document.getElementById("tblBajas").textContent =
    datos.kpi.bajas.toLocaleString();

document.getElementById("tblValor").textContent =
    "$ " + datos.kpi.valor.toLocaleString();

});