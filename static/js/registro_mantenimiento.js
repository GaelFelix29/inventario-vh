document.querySelectorAll("[data-document-upload]").forEach((form) => {
  const input = form.querySelector("[data-file-input]");
  const dropzone = form.querySelector("[data-dropzone]");
  const selected = form.querySelector("[data-selected-file]");
  const name = form.querySelector("[data-file-name]");
  const size = form.querySelector("[data-file-size]");
  const remove = form.querySelector("[data-file-remove]");
  const submit = form.querySelector("[data-upload-submit]");
  const allowed = ["application/pdf", "image/png", "image/jpeg"];
  const maximum = 10 * 1024 * 1024;

  const showFile = () => {
    const file = input.files[0];
    if (!file) {
      selected.hidden = true;
      submit.disabled = true;
      return;
    }
    if (!allowed.includes(file.type) || file.size > maximum) {
      input.value = "";
      selected.hidden = false;
      name.textContent = "Archivo no permitido";
      size.textContent = file.size > maximum ? "Supera el límite de 10 MB" : "Selecciona PDF, PNG o JPG";
      submit.disabled = true;
      return;
    }
    name.textContent = file.name;
    size.textContent = `${(file.size / 1024 / 1024).toFixed(2)} MB · Listo para subir`;
    selected.hidden = false;
    submit.disabled = false;
  };

  input.addEventListener("change", showFile);
  ["dragenter", "dragover"].forEach((eventName) => dropzone.addEventListener(eventName, (event) => {
    event.preventDefault();
    dropzone.classList.add("is-dragging");
  }));
  ["dragleave", "drop"].forEach((eventName) => dropzone.addEventListener(eventName, (event) => {
    event.preventDefault();
    dropzone.classList.remove("is-dragging");
  }));
  dropzone.addEventListener("drop", (event) => {
    if (!event.dataTransfer.files.length) return;
    const transfer = new DataTransfer();
    transfer.items.add(event.dataTransfer.files[0]);
    input.files = transfer.files;
    showFile();
  });
  remove.addEventListener("click", () => {
    input.value = "";
    selected.hidden = true;
    submit.disabled = true;
  });
  form.addEventListener("submit", () => {
    submit.classList.add("is-loading");
    submit.disabled = true;
    submit.querySelector("i").className = "bi bi-arrow-repeat";
    submit.querySelector("span").textContent = "Subiendo evidencia...";
  });
});
