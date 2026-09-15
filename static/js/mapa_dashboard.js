document.addEventListener("DOMContentLoaded", async () => {
    const panel = document.querySelector(".mapa-panel");
    if (!panel) return;
    const estado = document.getElementById("mapaEstado");
    const lista = document.getElementById("mapaLista");
    const buscar = document.getElementById("mapaBuscar");
    const todas = document.getElementById("mapaVerTodas");
    const elemento = (tag, texto, clase) => {
        const nodo = document.createElement(tag);
        if (texto !== undefined) nodo.textContent = texto;
        if (clase) nodo.className = clase;
        return nodo;
    };
    let mapa = null;
    let errorMapa = false;
    const pines = new Map();
    let seleccion = null;
    const normalizar = valor => valor.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toUpperCase();
    try {
        const respuesta = await fetch(panel.dataset.endpoint, {headers: {Accept: "application/json"}});
        if (!respuesta.ok || !respuesta.headers.get("content-type")?.includes("application/json")) throw new Error("datos");
        const datos = await respuesta.json();
        const resumen = datos.total + " activos · " + datos.localizadas + " sedes en el mapa" +
            (datos.sin_localizar ? " · " + datos.sin_localizar + " ubicaciones pendientes de coordenadas" : "");
        estado.textContent = datos.total ? resumen : "Todavía no hay activos registrados.";
        if (window.L) {
            mapa = L.map("mapaActivos", {scrollWheelZoom: false}).setView([23.94, -102.58], 5);
            L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
                maxZoom: 19,
                attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
            }).on("tileerror", () => {
                errorMapa = true;
                estado.textContent = "No se pudo cargar parte del mapa. Puede consultar las sedes en la leyenda.";
            }).addTo(mapa);
            datos.ubicaciones.forEach(sede => {
                if (!sede.coordenadas) return;
                const etiqueta = elemento("span", String(sede.total));
                etiqueta.style.backgroundColor = sede.color;
                const pin = L.marker(sede.coordenadas, {
                    title: sede.nombre + ": " + sede.total + " activos",
                    icon: L.divIcon({className: "mapa-pin", html: etiqueta, iconSize: [36, 36], iconAnchor: [18, 36]})
                }).addTo(mapa);
                const popup = elemento("div", undefined, "mapa-popup");
                popup.append(elemento("h3", sede.nombre), elemento("p", sede.total + " activos registrados"),
                    elemento("p", sede.activos + " en servicio · " + sede.bajas + " bajas"));
                if (sede.otros) popup.append(elemento("p", sede.otros + " en otros estados"));
                pin.bindPopup(popup).bindTooltip(elemento("span", sede.nombre), {direction: "top", offset: [0, -30]});
                pin.on("click", () => { seleccion = sede.nombre; pintarLista(); });
                pines.set(sede.nombre, pin);
            });
            new ResizeObserver(() => mapa.invalidateSize()).observe(document.getElementById("mapaActivos"));
        } else {
            errorMapa = true;
            estado.textContent = "El mapa no está disponible. Las cantidades por sede aparecen en la leyenda.";
        }
        function encuadrar() {
            if (!mapa || !pines.size) return;
            mapa.fitBounds(L.featureGroup([...pines.values()]).getBounds(), {padding: [38, 38], maxZoom: 15});
        }
        function pintarLista() {
            lista.replaceChildren();
            const coincidencias = datos.ubicaciones.filter(s => normalizar(s.nombre).includes(normalizar(buscar.value.trim())));
            coincidencias.forEach(sede => {
                const boton = elemento("button", undefined, "mapa-sede");
                boton.type = "button";
                boton.setAttribute("aria-pressed", String(seleccion === sede.nombre));
                const color = elemento("span", undefined, "mapa-sede__color");
                color.style.backgroundColor = sede.coordenadas ? sede.color : "#9ca9a1";
                const texto = elemento("span");
                texto.append(elemento("strong", sede.nombre), elemento("small", sede.coordenadas ?
                    sede.activos + " en servicio · " + sede.bajas + " bajas" : "Sin coordenadas confirmadas"));
                boton.append(color, texto, elemento("span", String(sede.total), "mapa-sede__total"));
                boton.addEventListener("click", () => {
                    seleccion = sede.nombre;
                    pintarLista();
                    const pin = pines.get(sede.nombre);
                    if (pin && mapa) { mapa.setView(pin.getLatLng(), 16); pin.openPopup(); }
                    if (!errorMapa) estado.textContent = sede.coordenadas ? resumen :
                        sede.nombre + ": " + sede.total + " activos. Falta confirmar la ubicación geográfica.";
                });
                lista.append(boton);
            });
            if (!coincidencias.length) lista.append(elemento("p", "No hay sedes que coincidan."));
        }
        pintarLista();
        buscar.addEventListener("input", pintarLista);
        todas.disabled = !pines.size;
        todas.addEventListener("click", () => {
            seleccion = null; buscar.value = ""; pintarLista(); encuadrar();
            if (!errorMapa) estado.textContent = resumen;
        });
        encuadrar();
    } catch (error) {
        estado.textContent = "No se pudieron cargar las ubicaciones. Actualice la página para reintentar.";
    }
});

