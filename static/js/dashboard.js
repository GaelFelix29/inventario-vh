document.addEventListener("DOMContentLoaded", async function () {

    const errorDashboard =
        document.getElementById("dashboardError");

    function establecerTexto(id, valor) {

        const elemento =
            document.getElementById(id);

        if (elemento) {
            elemento.textContent = valor;
        }

    }

    function formatearNumero(valor) {

        return Number(valor || 0).toLocaleString(
            "es-MX"
        );

    }

    function formatearMoneda(valor) {

        return new Intl.NumberFormat(
            "es-MX",
            {
                style: "currency",
                currency: "MXN",
                maximumFractionDigits: 0
            }
        ).format(
            Number(valor || 0)
        );

    }

    function opcionesGenerales() {

        return {
            responsive: true,
            maintainAspectRatio: false,
            animation: {
                duration: 800
            },
            plugins: {
                legend: {
                    position: "bottom",
                    labels: {
                        usePointStyle: true,
                        pointStyle: "circle",
                        padding: 18,
                        color: "#607068",
                        font: {
                            size: 11,
                            weight: "600"
                        }
                    }
                },
                tooltip: {
                    backgroundColor: "#173c2a",
                    padding: 12,
                    cornerRadius: 10,
                    titleFont: {
                        size: 12,
                        weight: "700"
                    },
                    bodyFont: {
                        size: 11
                    }
                }
            }
        };

    }

    try {

        const respuesta = await fetch(
            "/dashboard/datos",
            {
                headers: {
                    "Accept": "application/json"
                }
            }
        );

        if (!respuesta.ok) {

            throw new Error(
                "No fue posible consultar el dashboard."
            );

        }

        const datos = await respuesta.json();

        // ======================================
        // INDICADORES
        // ======================================

        establecerTexto(
            "totalActivos",
            formatearNumero(datos.kpi.total)
        );

        establecerTexto(
            "activos",
            formatearNumero(datos.kpi.activos)
        );

        establecerTexto(
            "bajas",
            formatearNumero(datos.kpi.bajas)
        );

        establecerTexto(
            "valor",
            formatearMoneda(datos.kpi.valor)
        );

        // ======================================
        // GRÁFICA POR ORIGEN
        // ======================================

        const opcionesOrigen =
            opcionesGenerales();

        opcionesOrigen.cutout = "62%";

        new Chart(
            document.getElementById("graficaOrigen"),
            {
                type: "doughnut",

                data: {
                    labels:
                        datos.origen.labels,

                    datasets: [{
                        data:
                            datos.origen.values,

                        backgroundColor: [
                            "#15945a",
                            "#32a9d6",
                            "#f2b638",
                            "#e65460",
                            "#8a5bd1",
                            "#f1843d",
                            "#21b4a4",
                            "#465f54"
                        ],

                        borderColor: "#ffffff",
                        borderWidth: 4,
                        hoverOffset: 7
                    }]
                },

                options: opcionesOrigen
            }
        );

        // ======================================
        // ESTADO DOCUMENTAL
        // ======================================

        const opcionesEstado =
            opcionesGenerales();

        opcionesEstado.plugins.legend.display =
            false;

        opcionesEstado.scales = {
            x: {
                grid: {
                    display: false
                },
                border: {
                    display: false
                },
                ticks: {
                    color: "#78877f",
                    font: {
                        size: 10
                    }
                }
            },
            y: {
                beginAtZero: true,
                border: {
                    display: false
                },
                grid: {
                    color: "#edf2ef"
                },
                ticks: {
                    precision: 0,
                    color: "#87948d"
                }
            }
        };

        new Chart(
            document.getElementById("graficaEstado"),
            {
                type: "bar",

                data: {
                    labels:
                        datos.documentacion.labels,

                    datasets: [{
                        label: "Documentación",

                        data:
                            datos.documentacion.values,

                        backgroundColor: "#16965b",
                        hoverBackgroundColor: "#0c7f4a",
                        borderRadius: 9,
                        borderSkipped: false,
                        maxBarThickness: 42
                    }]
                },

                options: opcionesEstado
            }
        );

        // ======================================
        // TOP 10 MAQUINARIAS
        // ======================================

        const opcionesTop =
            opcionesGenerales();

        opcionesTop.indexAxis = "y";
        opcionesTop.plugins.legend.display =
            false;

        opcionesTop.scales = {
            x: {
                beginAtZero: true,
                border: {
                    display: false
                },
                grid: {
                    color: "#edf2ef"
                },
                ticks: {
                    precision: 0,
                    color: "#87948d"
                }
            },
            y: {
                border: {
                    display: false
                },
                grid: {
                    display: false
                },
                ticks: {
                    color: "#53645b",
                    font: {
                        size: 10,
                        weight: "600"
                    }
                }
            }
        };

        new Chart(
            document.getElementById("graficaTop"),
            {
                type: "bar",

                data: {
                    labels:
                        datos.top.labels,

                    datasets: [{
                        label: "Cantidad",

                        data:
                            datos.top.values,

                        backgroundColor: [
                            "#15945a",
                            "#239f65",
                            "#31aa70",
                            "#45b47d",
                            "#59be89",
                            "#6dc896",
                            "#81d1a3",
                            "#96dab0",
                            "#abe3bd",
                            "#c0ebcb"
                        ],

                        hoverBackgroundColor:
                            "#087c48",

                        borderRadius: 8,
                        borderSkipped: false,
                        maxBarThickness: 28
                    }]
                },

                options: opcionesTop
            }
        );

        // ======================================
        // VALOR POR ORIGEN
        // ======================================

        const opcionesValor =
            opcionesGenerales();

        opcionesValor.cutout = "65%";

        opcionesValor.plugins.tooltip.callbacks = {
            label: function (contexto) {

                const valor =
                    contexto.parsed || 0;

                return (
                    contexto.label +
                    ": " +
                    formatearMoneda(valor)
                );

            }
        };

        new Chart(
            document.getElementById(
                "graficaValorOrigen"
            ),
            {
                type: "doughnut",

                data: {
                    labels:
                        datos.valorOrigen.labels,

                    datasets: [{
                        data:
                            datos.valorOrigen.values,

                        backgroundColor: [
                            "#15945a",
                            "#32a9d6",
                            "#f2b638",
                            "#e65460",
                            "#8a5bd1",
                            "#f1843d",
                            "#21b4a4",
                            "#465f54"
                        ],

                        borderColor: "#ffffff",
                        borderWidth: 4,
                        hoverOffset: 7
                    }]
                },

                options: opcionesValor
            }
        );

    } catch (error) {

        console.error(
            "ERROR CARGANDO DASHBOARD:",
            error
        );

        if (errorDashboard) {
            errorDashboard.hidden = false;
        }

    }

});