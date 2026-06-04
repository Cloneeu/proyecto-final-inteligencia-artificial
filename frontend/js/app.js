
document.addEventListener("DOMContentLoaded", () => {

  // Estado local de la UI
  let componentes = [];
  let conexiones = [];
  let herramienta = "seleccion";   // seleccion | componente | conexion
  let conexionParcial = null;       // primer componente al crear conexion por clic

  // Atajos para obtener elementos
  const $ = (id) => document.getElementById(id);

  // notificaciones
  let toastTimer = null;
  function avisar(mensaje, esError = false) {
    const t = $("toast");
    t.textContent = mensaje;
    t.style.background = esError
      ? getComputedStyle(document.documentElement).getPropertyValue("--error")
      : getComputedStyle(document.documentElement).getPropertyValue("--texto");
    t.classList.add("visible");
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => t.classList.remove("visible"), 2600);
  }

  // temas claro y oscuro
  function aplicarTema(tema) {
    document.documentElement.setAttribute("data-tema", tema);
    localStorage.setItem("pcb_tema", tema);
    $("btnTema").innerHTML = tema === "oscuro" ? "&#9728;" : "&#9790;";
    Lienzo.setTema(tema === "oscuro");
  }
  $("btnTema").addEventListener("click", () => {
    const actual = document.documentElement.getAttribute("data-tema");
    aplicarTema(actual === "oscuro" ? "claro" : "oscuro");
  });
  aplicarTema(localStorage.getItem("pcb_tema") || "oscuro");

  // inicializacion
  Lienzo.inicializar("canvas", "areaCanvas");

  Lienzo.onMoverCursor((celda) => {
    $("coordenadas").textContent = `X: ${celda.x}, Y: ${celda.y}`;
  });

  Lienzo.onClicCelda(async (celda) => {
    if (herramienta === "componente") {
      // Rellenamos las coordenadas y agregamos con los datos del formulario
      $("inpCompX").value = celda.x;
      $("inpCompY").value = celda.y;
      await agregarComponenteDesdeFormulario(true);
    } else if (herramienta === "conexion") {
      const comp = componenteEnCelda(celda);
      if (!comp) return;
      if (!conexionParcial) {
        conexionParcial = comp.id;
        avisar(`Origen: ${comp.id}. Elige el destino.`);
      } else if (conexionParcial !== comp.id) {
        await crearConexion(conexionParcial, comp.id);
        conexionParcial = null;
      }
    }
  });

  function componenteEnCelda(celda) {
    return componentes.find((c) =>
      celda.x >= c.x && celda.x < c.x + (c.ancho || 1) &&
      celda.y >= c.y && celda.y < c.y + (c.alto || 1)
    );
  }

  // slide bar
  const mapaHerr = {
    herrSeleccion: "seleccion",
    herrComponente: "componente",
    herrConexion: "conexion",
  };
  Object.keys(mapaHerr).forEach((id) => {
    $(id).addEventListener("click", () => {
      document.querySelectorAll(".herramienta").forEach(h => h.classList.remove("activa"));
      $(id).classList.add("activa");
      herramienta = mapaHerr[id];
      conexionParcial = null;
    });
  });
  $("herrAjustar").addEventListener("click", () => Lienzo.ajustar());


  async function cargarTodo() {
    try {
      const proyecto = await API.obtenerProyecto();
      aplicarProyecto(proyecto);
    } catch (e) {
      avisar("No se pudo cargar el proyecto", true);
    }
  }

  function aplicarProyecto(proyecto) {
    componentes = proyecto.componentes || [];
    conexiones = proyecto.conexiones || [];
    const placa = proyecto.placa || { filas: 30, columnas: 30, tamano_celda: 22 };
    $("nombreProyecto").textContent = proyecto.nombre || "proyecto_sin_nombre";
    $("inpFilas").value = placa.filas;
    $("inpColumnas").value = placa.columnas;
    $("inpTamCelda").value = placa.tamano_celda;
    Lienzo.setPlaca(placa);
    Lienzo.setComponentes(componentes);
    Lienzo.setRutas([]);
    Lienzo.ajustar();
    refrescarListas();
    actualizarStatsBasicas();
  }

  // placa
  $("btnAplicarPlaca").addEventListener("click", async () => {
    const config = {
      filas: parseInt($("inpFilas").value, 10),
      columnas: parseInt($("inpColumnas").value, 10),
      tamano_celda: parseInt($("inpTamCelda").value, 10),
    };
    try {
      const r = await API.configurarPlaca(config);
      Lienzo.setPlaca(r.placa);
      Lienzo.setRutas([]);
      Lienzo.ajustar();
      avisar("Placa actualizada");
    } catch (e) { avisar(e.message, true); }
  });

  // componentes
  async function agregarComponenteDesdeFormulario(autoId = false) {
    let id = $("inpCompId").value.trim();
    if (!id && autoId) {
      // Generamos un ID automatico si el usuario no escribio uno
      id = "C" + (componentes.length + 1);

      while (componentes.find(c => c.id === id)) {
      contador++;
      id = "C" + contador;
    }
    }
    if (!id) { avisar("Escribe un ID para el componente", true); return; }

    const comp = {
      id,
      nombre: $("inpCompNombre").value.trim() || id,
      tipo: $("inpCompTipo").value,
      x: parseInt($("inpCompX").value, 10) || 0,
      y: parseInt($("inpCompY").value, 10) || 0,
      ancho: parseInt($("inpCompAncho").value, 10) || 1,
      alto: parseInt($("inpCompAlto").value, 10) || 1,
      color: $("inpCompColor").value,
    };
    try {
      await API.crearComponente(comp);
      await recargarComponentesYConexiones();
      $("inpCompId").value = "";
      $("inpCompNombre").value = "";
      avisar(`Componente ${comp.id} agregado`);
    } catch (e) { avisar(e.message, true); }
  }
  $("btnAgregarComp").addEventListener("click", () => agregarComponenteDesdeFormulario());

  async function eliminarComponente(id) {
    try {
      await API.eliminarComponente(id);
      await recargarComponentesYConexiones();
      avisar(`Componente ${id} eliminado`);
    } catch (e) { avisar(e.message, true); }
  }

  async function recargarComponentesYConexiones() {
    componentes = await API.listarComponentes();
    conexiones = await API.listarConexiones();
    Lienzo.setComponentes(componentes);
    Lienzo.dibujar();
    refrescarListas();
    actualizarStatsBasicas();
  }

  // conexiones
  async function crearConexion(source, target) {
    try {
      await API.crearConexion({ source, target });
      await recargarComponentesYConexiones();
      avisar(`Conexion ${source} -> ${target} agregada`);
    } catch (e) { avisar(e.message, true); }
  }
  $("btnAgregarConexion").addEventListener("click", () => {
    const s = $("selOrigen").value, t = $("selDestino").value;
    if (!s || !t) { avisar("Selecciona origen y destino", true); return; }
    if (s === t) { avisar("Origen y destino no pueden ser iguales", true); return; }
    crearConexion(s, t);
  });

  // trazado de rutas
  $("btnRutear").addEventListener("click", async () => {
    if (conexiones.length === 0) { avisar("No hay conexiones que trazar", true); return; }
    const peticion = {
      algoritmo: $("selAlgoritmo").value,
      evitar_pistas: $("chkEvitarPistas").checked,
      permitir_diagonales: $("chkDiagonales").checked,
    };
    try {
      avisar("Calculando rutas...");
      const r = await API.rutear(peticion);

      // Animacion: juntamos los nodos de todas las rutas para mostrar la
      // expansion antes de pintar el resultado final
      const nodos = [];
      r.resultados.forEach(res => {
        if (res.camino) res.camino.forEach(c => nodos.push(c));
      });
      Lienzo.setRutas([]);
      Lienzo.animarExploracion(nodos, () => {
        Lienzo.setRutas(r.resultados);
        Lienzo.dibujar();
      });

      mostrarEstadisticas(r.estadisticas);
      mostrarAvisos(r.advertencias);
      const e = r.estadisticas;
      avisar(`${e.conexiones_completadas}/${e.conexiones_totales} rutas trazadas con ${e.algoritmo}`);
    } catch (err) { avisar(err.message, true); }
  });

  // borrar todo: limpia componentes, conexiones y rutas (conserva la placa)
  $("btnBorrarTodo").addEventListener("click", async () => {
    if (!confirm("¿Borrar todos los componentes, conexiones y rutas trazadas?")) return;
    try {
      const proyecto = await API.limpiarProyecto();
      Lienzo.setRutas([]);
      aplicarProyecto(proyecto);
      avisar("Todo borrado");
    } catch (e) { avisar(e.message, true); }
  });

  // ver PCB: alterna el lienzo entre vista esquematica y vista de placa real
  $("btnVerPCB").addEventListener("click", () => {
    const enPCB = Lienzo.toggleModoPCB();
    $("btnVerPCB").textContent = enPCB ? "Ver esquema" : "Ver PCB";
    $("btnVerPCB").classList.toggle("activo", enPCB);
  });

  // historial
  $("btnDeshacer").addEventListener("click", async () => {
    try { aplicarProyecto(await API.deshacer()); avisar("Deshecho"); }
    catch (e) { avisar(e.message, true); }
  });
  $("btnRehacer").addEventListener("click", async () => {
    try { aplicarProyecto(await API.rehacer()); avisar("Rehecho"); }
    catch (e) { avisar(e.message, true); }
  });

  // importar y exportar
  $("btnImportar").addEventListener("click", () => $("archivoImport").click());
  $("archivoImport").addEventListener("change", async (e) => {
    const archivo = e.target.files[0];
    if (!archivo) return;
    try {
      const r = await API.importar(archivo);
      aplicarProyecto(r.proyecto);
      avisar("Proyecto importado");
    } catch (err) { avisar(err.message, true); }
    e.target.value = "";
  });

  function descargar(url) {
    const a = document.createElement("a");
    a.href = url;
    document.body.appendChild(a);
    a.click();
    a.remove();
  }
  $("btnExportJson").addEventListener("click", () => descargar(API.urlExportJson()));
  $("btnExportImg").addEventListener("click", () => {
    const oscuro = document.documentElement.getAttribute("data-tema") === "oscuro";
    // Si estamos viendo el PCB, la imagen tambien sale como placa real
    descargar(API.urlExportImagen(oscuro, Lienzo.esModoPCB()));
  });
  $("btnExportPdf").addEventListener("click", () =>
    descargar(API.urlExportPdf(Lienzo.esModoPCB())));

  // nombre del proyecto
  $("nombreProyecto").addEventListener("click", () => {
    $("inpNuevoNombre").value = $("nombreProyecto").textContent;
    $("modalRenombrar").classList.add("abierto");
  });
  $("btnCancelarNombre").addEventListener("click", () =>
    $("modalRenombrar").classList.remove("abierto"));
  $("btnGuardarNombre").addEventListener("click", async () => {
    const nombre = $("inpNuevoNombre").value.trim();
    if (!nombre) return;
    try {
      await API.renombrar(nombre);
      $("nombreProyecto").textContent = nombre;
      $("modalRenombrar").classList.remove("abierto");
      avisar("Proyecto renombrado");
    } catch (e) { avisar(e.message, true); }
  });

  // zoom
  $("zoomMas").addEventListener("click", () => Lienzo.zoom(1.2));
  $("zoomMenos").addEventListener("click", () => Lienzo.zoom(0.8));
  $("zoomReset").addEventListener("click", () => Lienzo.ajustar());

  // listas y estadisticas
  function refrescarListas() {
    // Lista de componentes
    const lc = $("listaComponentes");
    lc.innerHTML = "";
    componentes.forEach((c) => {
      const div = document.createElement("div");
      div.className = "item";
      div.innerHTML = `
        <span class="punto" style="background:${c.color}"></span>
        <span class="info">
          <span class="id">${c.id}</span>
          <span class="sub">${c.tipo} · (${c.x},${c.y})</span>
        </span>
        <button class="borrar" title="Eliminar">&times;</button>`;
      div.querySelector(".borrar").addEventListener("click", () => eliminarComponente(c.id));
      lc.appendChild(div);
    });

    // Selectores de conexion
    const so = $("selOrigen"), sd = $("selDestino");
    so.innerHTML = ""; sd.innerHTML = "";
    componentes.forEach((c) => {
      so.appendChild(new Option(c.id, c.id));
      sd.appendChild(new Option(c.id, c.id));
    });

    // Lista de conexiones
    const lcx = $("listaConexiones");
    lcx.innerHTML = "";
    conexiones.forEach((cx) => {
      const div = document.createElement("div");
      div.className = "item";
      div.innerHTML = `
        <span class="info">
          <span class="id">${cx.source} &rarr; ${cx.target}</span>
        </span>`;
      lcx.appendChild(div);
    });
  }

  function actualizarStatsBasicas() {
    $("stComp").textContent = componentes.length;
    // Las estadisticas de ruteo se actualizan tras trazar
  }

  function mostrarEstadisticas(e) {
    $("stComp").textContent = e.componentes_totales;
    $("stConex").textContent = e.conexiones_completadas;
    $("stLong").textContent = e.longitud_promedio;
    $("stTiempo").textContent = e.tiempo_promedio_ms;
  }

  function mostrarAvisos(avisos) {
    const cont = $("avisos");
    const seccion = $("seccionAvisos");
    cont.innerHTML = "";
    if (!avisos || avisos.length === 0) {
      seccion.style.display = "none";
      return;
    }
    seccion.style.display = "block";
    avisos.forEach((a) => {
      const div = document.createElement("div");
      div.className = "aviso-item";
      div.textContent = a;
      cont.appendChild(div);
    });
  }

  cargarTodo();
});
