// ============================================================
// EVITAR ENVÍOS DOBLES EN LOS FORMULARIOS DEL MÓDULO
// ============================================================

document.querySelectorAll('.conjunto form').forEach(form => {

    form.addEventListener('submit', event => {

        if (event.defaultPrevented) return;

        // Si es el formulario para vincular un accesorio existente,
        // comprobamos que realmente se haya seleccionado uno.
        if (form.hasAttribute('data-buscar-contenido')) {

            const selected = form.querySelector('[data-contenido-id]');
            const results = form.querySelector('[data-contenido-resultados]');
            const input = form.querySelector('[data-contenido-busqueda]');

            if (!selected || !selected.value.trim()) {

                event.preventDefault();

                if (results) {
                    results.hidden = false;
                    results.textContent =
                        'Seleccione un accesorio de los resultados antes de vincular.';
                }

                if (input) {
                    input.focus();
                }

                return;
            }
        }

        // Evitar doble envío.
        if (form.dataset.enviando) {
            event.preventDefault();
            return;
        }

        form.dataset.enviando = '1';

        form.querySelectorAll('button[type="submit"]').forEach(button => {
            button.disabled = true;
            button.textContent = 'Guardando…';
        });
    });

});


// ============================================================
// BUSCADOR DE ACCESORIOS EXISTENTES
// ============================================================

document.querySelectorAll('[data-buscar-contenido]').forEach(form => {

    const input = form.querySelector('[data-contenido-busqueda]');
    const results = form.querySelector('[data-contenido-resultados]');
    const selected = form.querySelector('[data-contenido-id]');

    const selectedCard = form.querySelector('[data-contenido-seleccion]');
    const selectedId = form.querySelector('[data-contenido-seleccion-id]');
    const selectedDescription = form.querySelector(
        '[data-contenido-seleccion-descripcion]'
    );

    const changeButton = form.querySelector('[data-contenido-cambiar]');
    const submitButton = form.querySelector('button[type="submit"]');

    let timer = null;
    let controller = null;


    // ========================================================
    // REINICIAR SELECCIÓN
    // ========================================================

    function clearSelection() {

        selected.value = '';

        if (selectedCard) {
            selectedCard.hidden = true;
        }

        if (selectedId) {
            selectedId.textContent = '';
        }

        if (selectedDescription) {
            selectedDescription.textContent = '';
        }

        if (submitButton) {
            submitButton.disabled = true;
        }
    }


    // El botón de vincular permanece desactivado hasta
    // seleccionar un accesorio.
    if (submitButton) {
        submitButton.disabled = true;
    }


    // ========================================================
    // ESCRIBIR EN EL BUSCADOR
    // ========================================================

    input.addEventListener('input', () => {

        clearTimeout(timer);

        if (controller) {
            controller.abort();
        }

        clearSelection();

        results.hidden = false;
        results.replaceChildren();

        const query = input.value.trim();

        if (query.length < 2) {

            results.textContent =
                'Escriba al menos 2 caracteres para buscar.';

            return;
        }


        // Pequeño retraso para no consultar al servidor
        // con cada tecla inmediatamente.
        timer = setTimeout(async () => {

            controller = new AbortController();

            results.hidden = false;
            results.textContent = 'Buscando…';

            try {

                const url = new URL(
                    form.dataset.buscarContenido,
                    location.origin
                );

                url.searchParams.set('q', query);

                const response = await fetch(url, {
                    signal: controller.signal
                });

                if (!response.ok) {
                    throw new Error('search');
                }

                const items = await response.json();


                // Si mientras llegaba la respuesta el usuario
                // cambió el texto, ignoramos la respuesta anterior.
                if (input.value.trim() !== query) {
                    return;
                }


                results.replaceChildren();


                // ====================================================
                // CREAR RESULTADOS
                // ====================================================

                items.forEach(item => {

                    const button = document.createElement('button');

                    button.type = 'button';

                    button.textContent = [
                        item.id,
                        item.descripcion || 'Sin descripción',
                        item.marca,
                        item.modelo,
                        item.numero_serie
                    ]
                        .filter(Boolean)
                        .join(' · ');


                    // ================================================
                    // SELECCIONAR ACCESORIO
                    // ================================================

                    button.addEventListener('click', () => {

                        selected.value = item.id;


                        // Mostrar ID seleccionado.
                        if (selectedId) {
                            selectedId.textContent = item.id;
                        }


                        // Mostrar información descriptiva.
                        if (selectedDescription) {

                            selectedDescription.textContent = [
                                item.descripcion || 'Sin descripción',
                                item.marca,
                                item.modelo,
                                item.numero_serie
                            ]
                                .filter(Boolean)
                                .join(' · ');
                        }


                        // Mostrar tarjeta.
                        if (selectedCard) {
                            selectedCard.hidden = false;
                        }


                        // Ocultar lista de resultados.
                        results.replaceChildren();
                        results.hidden = true;


                        // Habilitar botón de vincular.
                        if (submitButton) {
                            submitButton.disabled = false;
                        }
                    });


                    results.append(button);
                });


                // ====================================================
                // SIN RESULTADOS
                // ====================================================

                if (!items.length) {

                    results.textContent =
                        'No se encontraron accesorios disponibles con esta búsqueda.';
                }

            } catch (error) {

                if (
                    error.name !== 'AbortError' &&
                    input.value.trim() === query
                ) {

                    results.hidden = false;

                    results.textContent =
                        'No se pudo realizar la búsqueda. Inténtelo de nuevo.';
                }
            }

        }, 300);

    });


    // ========================================================
    // CAMBIAR ACCESORIO SELECCIONADO
    // ========================================================

    if (changeButton) {

        changeButton.addEventListener('click', () => {

            clearSelection();

            input.value = '';

            results.hidden = false;

            results.textContent =
                'Escriba al menos 2 caracteres para buscar.';

            input.focus();
        });
    }

});