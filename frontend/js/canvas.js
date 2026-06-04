

const Lienzo = (() => {
  let canvas, ctx, contenedor;
  let placa = { filas: 30, columnas: 30, tamano_celda: 22 };
  let componentes = [];
  let rutas = [];            // resultados del ultimo ruteo
  let temaOscuro = true;
  let modoPCB = false;       // false = vista esquematica, true = vista placa real
  let pinSeleccionado = null; // patita de origen al crear una conexion {compId, idx}

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

    // En modo PCB pintamos el area de la placa como mascara de soldadura verde
    if (modoPCB) {
      ctx.fillStyle = "#0b6e3d";
      ctx.fillRect(offsetX, offsetY, placa.columnas * tc, placa.filas * tc);
    }

    // Cuadricula (se oculta en modo PCB para que la placa se vea limpia)
    if (!modoPCB) {
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
    }

    // Animacion de nodos explorados (solo en vista esquematica)
    if (animacion && !modoPCB) {
      ctx.fillStyle = temaOscuro ? "rgba(59,130,246,0.25)" : "rgba(37,99,235,0.18)";
      const limite = animacion.indice;
      for (let i = 0; i < limite && i < animacion.nodos.length; i++) {
        const [nx, ny] = animacion.nodos[i];
        ctx.fillRect(offsetX + nx * tc + 1, offsetY + ny * tc + 1, tc - 2, tc - 2);
      }
    }

    // Pistas trazadas. En modo PCB se ven como cobre (una sola capa).
    rutas.forEach((r) => {
      if (!r.exito || !r.camino || r.camino.length < 2) return;
      if (modoPCB) {
        ctx.strokeStyle = "#d9a441";       // color cobre/dorado
        ctx.lineWidth = Math.max(3, tc * 0.3);
      } else {
        ctx.strokeStyle = r.color || "#22c55e";
        ctx.lineWidth = Math.max(2, tc * 0.18);
      }
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

    // Componentes: simbolo electronico en esquematico, footprint en modo PCB
    componentes.forEach((comp) => {
      const x = offsetX + comp.x * tc;
      const y = offsetY + comp.y * tc;
      const cw = (comp.ancho || 1) * tc;
      const ch = (comp.alto || 1) * tc;
      if (modoPCB) {
        dibujarFootprint(x, y, cw, ch, tc, comp);
      } else {
        dibujarSimbolo(comp.tipo, x, y, cw, ch, tc, comp);
      }
      dibujarPines(comp, tc);
    });
  }

  // Dibuja un punto por cada patita del componente (pad dorado en modo PCB)
  function dibujarPines(comp, tc) {
    const radio = modoPCB ? Math.max(2, tc * 0.28) : Math.max(2, tc * 0.16);
    const color = modoPCB ? "#d9a441" : (comp.color || "#3b82f6");
    pinesDe(comp).forEach((p, idx) => {
      const px = offsetX + p.cx * tc + tc / 2;
      const py = offsetY + p.cy * tc + tc / 2;
      ctx.beginPath();
      ctx.arc(px, py, radio, 0, Math.PI * 2);
      ctx.fillStyle = color;
      ctx.fill();
      // Resaltamos la patita de origen elegida para la conexion
      if (pinSeleccionado &&
          pinSeleccionado.compId === comp.id && pinSeleccionado.idx === idx) {
        ctx.strokeStyle = "#ef4444";
        ctx.lineWidth = Math.max(1.5, tc * 0.1);
        ctx.beginPath();
        ctx.arc(px, py, radio + Math.max(2, tc * 0.14), 0, Math.PI * 2);
        ctx.stroke();
      }
    });
  }

  // Calcula las celdas de ruteo de las patitas (misma regla que el backend)
  function pinesDe(comp) {
    const x = comp.x, y = comp.y, w = comp.ancho || 1, h = comp.alto || 1;
    const midY = y + Math.floor(h / 2);
    const tipo = comp.tipo;

    if (tipo === "transistor") {
      return [{ cx: x - 1, cy: midY }, { cx: x + w, cy: y },
              { cx: x + w, cy: y + Math.max(1, h - 1) }];
    }
    if (tipo === "microcontrolador" || tipo === "integrado") {
      const n = Math.max(2, comp.pines || 2);
      const k = Math.floor((n + 1) / 2);   // mitad (o una mas) a la izquierda
      const pines = [];
      for (let i = 0; i < k; i++) {
        const fila = y + Math.min(h - 1, Math.floor((i + 0.5) * h / k));
        pines.push({ cx: x - 1, cy: fila });
      }
      const der = n - k;
      for (let i = 0; i < der; i++) {
        const fila = y + Math.min(h - 1, Math.floor((i + 0.5) * h / der));
        pines.push({ cx: x + w, cy: fila });
      }
      return pines;
    }
    if (tipo === "conector") {
      const n = Math.max(2, comp.pines || 2);
      const pines = [];
      for (let i = 0; i < n; i++) {
        const col = x + Math.min(w - 1, Math.floor((i + 0.5) * w / n));
        pines.push({ cx: col, cy: y + h });
      }
      return pines;
    }
    // resistencia, capacitor, diodo, led y "otro": 2 patitas izquierda/derecha
    return [{ cx: x - 1, cy: midY }, { cx: x + w, cy: midY }];
  }

  // Devuelve la patita mas cercana a la celda clicada, o null si esta lejos
  function pinEnCelda(celda) {
    let mejor = null, mejorDist = Infinity;
    componentes.forEach((comp) => {
      pinesDe(comp).forEach((p, idx) => {
        const d = Math.max(Math.abs(p.cx - celda.x), Math.abs(p.cy - celda.y));
        if (d < mejorDist) { mejorDist = d; mejor = { compId: comp.id, idx }; }
      });
    });
    return mejorDist <= 1 ? mejor : null;
  }

  // ------------------------------------------------------------------
  // Dibujo de simbolos electronicos (vista esquematica)
  // ------------------------------------------------------------------

  // Escribe el ID del componente si hay espacio suficiente
  function dibujarEtiqueta(texto, x, y, tc) {
    if (tc <= 14) return;
    ctx.fillStyle = temaOscuro ? "#e5e7eb" : "#1f2933";
    ctx.font = `${Math.max(9, tc * 0.4)}px Segoe UI, sans-serif`;
    ctx.textBaseline = "top";
    ctx.fillText(texto, x + 3, y + 3);
  }

  // Elige el simbolo segun el tipo del componente
  function dibujarSimbolo(tipo, x, y, w, h, tc, comp) {
    const color = comp.color || "#3b82f6";
    ctx.lineWidth = Math.max(1.5, tc * 0.12);
    ctx.lineJoin = "round";
    ctx.lineCap = "round";

    switch (tipo) {
      case "resistencia": dibujarResistencia(x, y, w, h, color); break;
      case "capacitor":   dibujarCapacitor(x, y, w, h, color); break;
      case "led":         dibujarDiodo(x, y, w, h, color, true); break;
      case "diodo":       dibujarDiodo(x, y, w, h, color, false); break;
      case "transistor":  dibujarTransistor(x, y, w, h, color); break;
      case "conector":    dibujarConector(x, y, w, h, color); break;
      case "microcontrolador":
      case "integrado":   dibujarChip(x, y, w, h, color); break;
      default:            dibujarGenerico(x, y, w, h, color); break;
    }
    dibujarEtiqueta(comp.id, x, y, tc);
  }

  // Resistencia: zigzag horizontal con dos terminales
  function dibujarResistencia(x, y, w, h, color) {
    ctx.strokeStyle = color;
    const cy = y + h / 2;
    const x0 = x + w * 0.18, x1 = x + w * 0.82;
    const ancho = x1 - x0;
    const amp = h * 0.22;
    const picos = 6;
    ctx.beginPath();
    ctx.moveTo(x, cy);          // terminal izquierdo
    ctx.lineTo(x0, cy);
    for (let i = 0; i < picos; i++) {
      const px = x0 + ancho * (i + 0.5) / picos;
      const py = cy + (i % 2 === 0 ? -amp : amp);
      ctx.lineTo(px, py);
    }
    ctx.lineTo(x1, cy);
    ctx.lineTo(x + w, cy);      // terminal derecho
    ctx.stroke();
  }

  // Capacitor: dos placas paralelas con terminales
  function dibujarCapacitor(x, y, w, h, color) {
    ctx.strokeStyle = color;
    const cy = y + h / 2;
    const gap = w * 0.1;
    const xa = x + w / 2 - gap, xb = x + w / 2 + gap;
    const mitad = h * 0.3;   // media altura de cada placa
    ctx.beginPath();
    ctx.moveTo(x, cy); ctx.lineTo(xa, cy);          // terminal izquierdo
    ctx.moveTo(xb, cy); ctx.lineTo(x + w, cy);      // terminal derecho
    ctx.moveTo(xa, cy - mitad); ctx.lineTo(xa, cy + mitad);  // placa izquierda
    ctx.moveTo(xb, cy - mitad); ctx.lineTo(xb, cy + mitad);  // placa derecha
    ctx.stroke();
  }

  // Diodo/LED: triangulo + barra de catodo. Si es LED, agrega flechas de luz.
  function dibujarDiodo(x, y, w, h, color, esLed) {
    ctx.strokeStyle = color;
    const cy = y + h / 2;
    const tx0 = x + w * 0.32, tx1 = x + w * 0.64;
    const th = h * 0.28;
    // terminales
    ctx.beginPath();
    ctx.moveTo(x, cy); ctx.lineTo(tx0, cy);
    ctx.moveTo(tx1, cy); ctx.lineTo(x + w, cy);
    ctx.stroke();
    // triangulo apuntando a la derecha
    ctx.beginPath();
    ctx.moveTo(tx0, cy - th);
    ctx.lineTo(tx0, cy + th);
    ctx.lineTo(tx1, cy);
    ctx.closePath();
    ctx.stroke();
    // barra del catodo
    ctx.beginPath();
    ctx.moveTo(tx1, cy - th); ctx.lineTo(tx1, cy + th);
    ctx.stroke();
    // flechas que indican luz (solo LED)
    if (esLed) {
      const ax = x + w * 0.5;
      ctx.beginPath();
      ctx.moveTo(ax, cy - th); ctx.lineTo(ax + w * 0.12, cy - th - h * 0.24);
      ctx.moveTo(ax + w * 0.14, cy - th); ctx.lineTo(ax + w * 0.26, cy - th - h * 0.24);
      ctx.stroke();
    }
  }

  // Transistor: circulo con base, colector y emisor
  function dibujarTransistor(x, y, w, h, color) {
    ctx.strokeStyle = color;
    const cx = x + w / 2, cy = y + h / 2;
    const r = Math.min(w, h) * 0.32;
    ctx.beginPath();
    ctx.arc(cx, cy, r, 0, Math.PI * 2);
    ctx.stroke();
    const bx = cx - r * 0.35;
    ctx.beginPath();
    ctx.moveTo(x, cy); ctx.lineTo(bx, cy);                 // base
    ctx.moveTo(bx, cy - r * 0.6); ctx.lineTo(bx, cy + r * 0.6);
    ctx.moveTo(bx, cy - r * 0.25); ctx.lineTo(cx + r * 0.5, cy - r * 0.6);
    ctx.lineTo(cx + r * 0.5, y);                           // colector
    ctx.moveTo(bx, cy + r * 0.25); ctx.lineTo(cx + r * 0.5, cy + r * 0.6);
    ctx.lineTo(cx + r * 0.5, y + h);                       // emisor
    ctx.stroke();
  }

  // Microcontrolador / integrado: cuerpo con patitas y punto del pin 1
  function dibujarChip(x, y, w, h, color) {
    const m = Math.min(w, h) * 0.18;
    const bx = x + m, by = y + m, bw = w - 2 * m, bh = h - 2 * m;
    // cuerpo del chip
    ctx.fillStyle = temaOscuro ? "#374151" : "#475569";
    ctx.strokeStyle = color;
    ctx.beginPath();
    ctx.rect(bx, by, bw, bh);
    ctx.fill();
    ctx.stroke();
    // patitas a izquierda y derecha
    ctx.strokeStyle = temaOscuro ? "#cbd5e1" : "#334155";
    const pines = Math.max(2, Math.floor(bh / (m * 1.4)));
    ctx.beginPath();
    for (let i = 0; i < pines; i++) {
      const py = by + bh * (i + 0.5) / pines;
      ctx.moveTo(x, py); ctx.lineTo(bx, py);
      ctx.moveTo(bx + bw, py); ctx.lineTo(x + w, py);
    }
    ctx.stroke();
    // punto indicador del pin 1
    ctx.fillStyle = color;
    ctx.beginPath();
    ctx.arc(bx + m * 0.7, by + m * 0.7, Math.max(1.5, m * 0.28), 0, Math.PI * 2);
    ctx.fill();
  }

  // Conector: cuerpo con una fila de pines
  function dibujarConector(x, y, w, h, color) {
    const m = Math.min(w, h) * 0.18;
    ctx.strokeStyle = color;
    ctx.fillStyle = temaOscuro ? "#1f2933" : "#e5e7eb";
    ctx.beginPath();
    ctx.rect(x + m, y + m, w - 2 * m, h - 2 * m);
    ctx.fill();
    ctx.stroke();
    const ancho = w - 2 * m;
    const pines = Math.max(2, Math.floor(ancho / (m * 1.6)));
    const cy = y + h / 2;
    ctx.fillStyle = color;
    for (let i = 0; i < pines; i++) {
      const px = x + m + ancho * (i + 0.5) / pines;
      ctx.beginPath();
      ctx.arc(px, cy, Math.max(1.5, m * 0.3), 0, Math.PI * 2);
      ctx.fill();
    }
  }

  // Generico ("otro"): el rectangulo redondeado de color de siempre
  function dibujarGenerico(x, y, w, h, color) {
    ctx.fillStyle = color;
    ctx.strokeStyle = temaOscuro ? "#ffffff" : "#1f2933";
    const r = Math.min(4, Math.min(w, h) * 0.2);
    ctx.beginPath();
    ctx.roundRect(x + 1, y + 1, w - 2, h - 2, r);
    ctx.fill();
    ctx.stroke();
  }

  // Footprint para la vista PCB: contorno de serigrafia (los pads van en las patitas)
  function dibujarFootprint(x, y, w, h, tc, comp) {
    // contorno blanco de serigrafia
    ctx.strokeStyle = "#e8eef2";
    ctx.lineWidth = Math.max(1, tc * 0.08);
    ctx.strokeRect(x + 2, y + 2, w - 4, h - 4);
    // etiqueta de serigrafia en blanco
    if (tc > 14) {
      ctx.fillStyle = "#e8eef2";
      ctx.font = `${Math.max(9, tc * 0.4)}px Segoe UI, sans-serif`;
      ctx.textBaseline = "top";
      ctx.fillText(comp.id, x + 3, y + 3);
    }
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
    // Alterna entre vista esquematica y vista PCB; devuelve el estado nuevo
    toggleModoPCB: () => { modoPCB = !modoPCB; dibujar(); return modoPCB; },
    setModoPCB: (v) => { modoPCB = v; dibujar(); },
    esModoPCB: () => modoPCB,
    // Patitas: consulta de cual se clico y resaltado de la patita de origen
    pinEnCelda: (celda) => pinEnCelda(celda),
    pinesDe: (comp) => pinesDe(comp),
    setPinSeleccionado: (pin) => { pinSeleccionado = pin; dibujar(); },
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
