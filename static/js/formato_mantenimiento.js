document.querySelectorAll("canvas[data-signature]").forEach((canvas) => {
  const hidden = document.getElementById(canvas.dataset.signature);
  const ctx = canvas.getContext("2d");
  let drawing = false;
  const resize = () => {
    const saved = hidden.value;
    const ratio = Math.max(window.devicePixelRatio || 1, 1);
    canvas.width = canvas.clientWidth * ratio;
    canvas.height = canvas.clientHeight * ratio;
    ctx.setTransform(ratio, 0, 0, ratio, 0, 0);
    ctx.lineWidth = 2;
    ctx.lineCap = "round";
    ctx.strokeStyle = "#123d2b";
    if (saved) { const img = new Image(); img.onload = () => ctx.drawImage(img, 0, 0, canvas.clientWidth, canvas.clientHeight); img.src = saved; }
  };
  resize();
  const point = (event) => { const box = canvas.getBoundingClientRect(); return {x:event.clientX-box.left,y:event.clientY-box.top}; };
  canvas.addEventListener("pointerdown", (event) => { if (canvas.closest("form")?.querySelector(".fm-actions") === null) return; drawing=true; canvas.setPointerCapture(event.pointerId); const p=point(event); ctx.beginPath(); ctx.moveTo(p.x,p.y); });
  canvas.addEventListener("pointermove", (event) => { if(!drawing)return; const p=point(event); ctx.lineTo(p.x,p.y); ctx.stroke(); });
  const stop = () => { if(!drawing)return; drawing=false; hidden.value=canvas.toDataURL("image/png"); };
  canvas.addEventListener("pointerup", stop); canvas.addEventListener("pointercancel", stop);
  document.querySelector(`[data-clear="${canvas.dataset.signature}"]`)?.addEventListener("click", () => { ctx.clearRect(0,0,canvas.width,canvas.height); hidden.value=""; });
});
