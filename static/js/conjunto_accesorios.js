document.querySelectorAll('.conjunto form').forEach(form => {
  form.addEventListener('submit', event => {
    if (event.defaultPrevented) return;
    if (form.dataset.enviando) { event.preventDefault(); return; }
    form.dataset.enviando = '1';
    form.querySelectorAll('button[type="submit"]').forEach(button => {
      button.disabled = true;
      button.textContent = 'Guardando…';
    });
  });
});
document.querySelectorAll('[data-buscar-contenido]').forEach(form => {
  const input = form.querySelector('[data-contenido-busqueda]');
  const results = form.querySelector('[data-contenido-resultados]');
  const selected = form.querySelector('[data-contenido-id]');
  let timer, controller;
  input.addEventListener('input', () => {
    clearTimeout(timer);
    if (controller) controller.abort();
    results.replaceChildren();
    selected.value = '';
    const query = input.value.trim();
    if (query.length < 2) {
      results.textContent = 'Escriba al menos 2 caracteres para buscar.';
      return;
    }
    timer = setTimeout(async () => {
      controller = new AbortController();
      results.textContent = 'Buscando…';
      try {
        const url = new URL(form.dataset.buscarContenido, location.origin);
        url.searchParams.set('q', query);
        const response = await fetch(url, {signal: controller.signal});
        if (!response.ok) throw new Error('search');
        const items = await response.json();
        if (input.value.trim() !== query) return;
        results.replaceChildren();
        items.forEach(item => {
          const button = document.createElement('button');
          button.type = 'button';
          button.textContent = [item.id, item.descripcion || 'Sin descripción', item.marca, item.modelo, item.numero_serie].filter(Boolean).join(' · ');
          button.addEventListener('click', () => {
            selected.value = item.id;
            results.textContent = `Seleccionado: ${item.id}. Se validará su disponibilidad al vincular.`;
          });
          results.append(button);
        });
        if (!items.length) results.textContent = 'Sin resultados. También puede escribir el ID exacto.';
      } catch (error) {
        if (error.name !== 'AbortError' && input.value.trim() === query) results.textContent = 'No se pudo buscar. Escriba el ID o inténtelo de nuevo.';
      }
    }, 300);
  });
});
