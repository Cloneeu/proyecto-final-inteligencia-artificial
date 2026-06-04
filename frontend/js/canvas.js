

const Lienzo = (() => {
  let canvas, ctx, contenedor;
  let placa = { filas: 30, columnas: 30, tamano_celda: 22 };
  let componentes = [];
  let rutas = [];            // resultados del ultimo ruteo
  let temaOscuro = true;

  // Transformacion de vista
  let escala = 1;
  let offsetX = 0;
  let offsetY = 0;

  // Estado de animacion de exploracion
  let animacion = null;

  // Callbacks que app.js registra para reaccionar a eventos del canvas
  let alHacerClicCelda = null;
  let alMoverCursor = null;

  function colores() {
    const css = getComputedStyle(document.documentElement);
    return {
      fondo: css.getPropertyValue("--fondo-canvas").trim(),
      grid: css.getPropertyValue("--grid-linea").trim(),
      gridMayor: css.getPropertyValue("--grid-mayor").trim(),
      texto: css.getPropertyValue("--texto").trim(),
    };
  }

  // Ajusta el tamano del canvas al contenedor (responsive y HiDPI)
  function redimensionar() {
    const rect = contenedor.getBoundingClientRect();
    const dpr = window.devicePixelRatio || 1;
    canvas.width = rect.width * dpr;
    canvas.height = rect.height * dpr;
    canvas.style.width = rect.width + "px";
    canvas.style.height = rect.height + "px";
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    dibujar();
  }

  // Convierte coordenadas de pantalla a celda de la cuadricula
  function pantallaACelda(px, py) {
    const tc = placa.tamano_celda * escala;
    const x = Math.floor((px - offsetX) / tc);
    const y = Math.floor((py - offsetY) / tc);
    return { x, y };
  }

  // Dibuja todo el contenido
  function dibujar() {
    if (!ctx) return;
    const c = colores();
    const tc = placa.tamano_celda * escala;
    const w = canvas.clientWidth;
    const h = canvas.clientHeight;

    ctx.clearRect(0, 0, w, h);
    ctx.fillStyle = c.fondo;
    ctx.fillRect(0, 0, w, h);

    // Cuadricula
    ctx.lineWidth = 1;
    for (let col = 0; col <= placa.columnas; col++) {
      const x = offsetX + col * tc;
      if (x < -tc || x > w + tc) continue;
      ctx.strokeStyle = (col % 5 === 0) ? c.gridMayor : c.grid;
      ctx.beginPath();
      ctx.moveTo(x, offsetY);
      ctx.lineTo(x, offsetY + placa.filas * tc);
      ctx.stroke();
    }
    for (let fila = 0; fila <= placa.filas; fila++) {
      const y = offsetY + fila * tc;
      if (y < -tc || y > h + tc) continue;
      ctx.strokeStyle = (fila % 5 === 0) ? c.gridMayor : c.grid;
      ctx.beginPath();
      ctx.moveTo(offsetX, y);
      ctx.lineTo(offsetX + placa.columnas * tc, y);
      ctx.stroke();
    }

    // Animacion de nodos explorados (se dibuja debajo de las pistas finales)
    if (animacion) {
      ctx.fillStyle = temaOscuro ? "rgba(59,130,246,0.25)" : "rgba(37,99,235,0.18)";
      const limite = animacion.indice;
      for (let i = 0; i < limite && i < animacion.nodos.length; i++) {
        const [nx, ny] = animacion.nodos[i];
        ctx.fillRect(offsetX + nx * tc + 1, offsetY + ny * tc + 1, tc - 2, tc - 2);
      }
    }

    // Pistas trazadas
    rutas.forEach((r) => {
      if (!r.exito || !r.camino || r.camino.length < 2) return;
      ctx.strokeStyle = r.color || "#22c55e";
      ctx.lineWidth = Math.max(2, tc * 0.18);
      ctx.lineJoin = "round";
      ctx.lineCap = "round";
      ctx.beginPath();
      r.camino.forEach(([cx, cy], i) => {
        const px = offsetX + cx * tc + tc / 2;
        const py = offsetY + cy * tc + tc / 2;
        if (i === 0) ctx.moveTo(px, py);
        else ctx.lineTo(px, py);
      });
      ctx.stroke();
    });

    // Componentes
    componentes.forEach((comp) => {
      const x = offsetX + comp.x * tc;
      const y = offsetY + comp.y * tc;
      const cw = (comp.ancho || 1) * tc;
      const ch = (comp.alto || 1) * tc;
      ctx.fillStyle = comp.color || "#3b82f6";
      ctx.strokeStyle = temaOscuro ? "#ffffff" : "#1f2933";
      ctx.lineWidth = 1.5;
      // Rectangulo redondeado
      const r = Math.min(4, tc * 0.2);
      ctx.beginPath();
      ctx.roundRect(x + 1, y + 1, cw - 2, ch - 2, r);
      ctx.fill();
      ctx.stroke();
      // Etiqueta con el ID si hay espacio
      if (tc > 14) {
        ctx.fillStyle = "#ffffff";
        ctx.font = `${Math.max(9, tc * 0.42)}px Segoe UI, sans-serif`;
        ctx.textBaseline = "top";
        ctx.fillText(comp.id, x + 3, y + 3);
      }
    });
  }

  // Anima la exploracion de nodos antes de mostrar la ruta final
  function animarExploracion(todosLosNodos, alTerminar) {
    animacion = { nodos: todosLosNodos, indice: 0 };
    const paso = Math.max(1, Math.floor(todosLosNodos.length / 60));
    function tick() {
      animacion.indice += paso;
      dibujar();
      if (animacion.indice < todosLosNodos.length) {
        requestAnimationFrame(tick);
      } else {
        animacion = null;
        dibujar();
        if (alTerminar) alTerminar();
      }
    }
    requestAnimationFrame(tick);
  }

  // Centra y ajusta el zoom para que la placa quepa en pantalla
  function ajustar() {
    const w = canvas.clientWidth;
    const h = canvas.clientHeight;
    const anchoPlaca = placa.columnas * placa.tamano_celda;
    const altoPlaca = placa.filas * placa.tamano_celda;
    const margen = 40;
    escala = Math.min((w - margen) / anchoPlaca, (h - margen) / altoPlaca, 3);
    if (!isFinite(escala) || escala <= 0) escala = 1;
    offsetX = (w - anchoPlaca * escala) / 2;
    offsetY = (h - altoPlaca * escala) / 2;
    dibujar();
  }

  function inicializar(idCanvas, idContenedor) {
    canvas = document.getElementById(idCanvas);
    contenedor = document.getElementById(idContenedor);
    ctx = canvas.getContext("2d");

    window.addEventListener("resize", redimensionar);

    // clic notificamos la celda
    canvas.addEventListener("click", (e) => {
      const rect = canvas.getBoundingClientRect();
      const celda = pantallaACelda(e.clientX - rect.left, e.clientY - rect.top);
      if (alHacerClicCelda &&
          celda.x >= 0 && celda.x < placa.columnas &&
          celda.y >= 0 && celda.y < placa.filas) {
        alHacerClicCelda(celda);
      }
    });

    // Movimiento: actualizamos coordenadas
    canvas.addEventListener("mousemove", (e) => {
      const rect = canvas.getBoundingClientRect();
      const celda = pantallaACelda(e.clientX - rect.left, e.clientY - rect.top);
      if (alMoverCursor) alMoverCursor(celda);
    });

    // Zoom con rueda del raton, centrado en el cursor
    canvas.addEventListener("wheel", (e) => {
      e.preventDefault();
      const rect = canvas.getBoundingClientRect();
      const mx = e.clientX - rect.left;
      const my = e.clientY - rect.top;
      const factor = e.deltaY < 0 ? 1.1 : 0.9;
      const nuevaEscala = Math.min(Math.max(escala * factor, 0.2), 6);
      // Mantenemos el punto bajo el cursor fijo al hacer zoom
      offsetX = mx - (mx - offsetX) * (nuevaEscala / escala);
      offsetY = my - (my - offsetY) * (nuevaEscala / escala);
      escala = nuevaEscala;
      dibujar();
    }, { passive: false });

    // Pan con boton central o con la tecla espacio + arrastrar
    let arrastrando = false, ultimoX = 0, ultimoY = 0;
    canvas.addEventListener("mousedown", (e) => {
      if (e.button === 1 || e.shiftKey) {
        arrastrando = true; ultimoX = e.clientX; ultimoY = e.clientY;
        canvas.style.cursor = "grabbing";
        e.preventDefault();
      }
    });
    window.addEventListener("mousemove", (e) => {
      if (!arrastrando) return;
      offsetX += e.clientX - ultimoX;
      offsetY += e.clientY - ultimoY;
      ultimoX = e.clientX; ultimoY = e.clientY;
      dibujar();
    });
    window.addEventListener("mouseup", () => {
      arrastrando = false;
      canvas.style.cursor = "crosshair";
    });

    redimensionar();
  }

  return {
    inicializar,
    setPlaca: (p) => { placa = p; },
    setComponentes: (c) => { componentes = c; },
    setRutas: (r) => { rutas = r; },
    setTema: (oscuro) => { temaOscuro = oscuro; dibujar(); },
    dibujar,
    ajustar,
    animarExploracion,
    zoom: (factor) => {
      const w = canvas.clientWidth / 2, h = canvas.clientHeight / 2;
      const nueva = Math.min(Math.max(escala * factor, 0.2), 6);
      offsetX = w - (w - offsetX) * (nueva / escala);
      offsetY = h - (h - offsetY) * (nueva / escala);
      escala = nueva; dibujar();
    },
    onClicCelda: (cb) => { alHacerClicCelda = cb; },
    onMoverCursor: (cb) => { alMoverCursor = cb; },
  };
})();
