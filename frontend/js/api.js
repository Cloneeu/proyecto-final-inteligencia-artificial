
const API = (() => {
  const BASE = "/api";

  // Envoltura generica para peticiones JSON con manejo de error uniforme
  async function pedir(ruta, opciones = {}) {
    const resp = await fetch(BASE + ruta, {
      headers: { "Content-Type": "application/json" },
      ...opciones,
    });
    if (!resp.ok) {
      let detalle = "Error en la peticion";
      try {
        const j = await resp.json();
        detalle = j.detail || detalle;
      } catch (e) { /* respuesta sin cuerpo JSON */ }
      throw new Error(detalle);
    }
    return resp.json();
  }

  return {
    // Placa
    obtenerPlaca: () => pedir("/placa"),
    configurarPlaca: (config) =>
      pedir("/placa", { method: "POST", body: JSON.stringify(config) }),

    // Algoritmos
    listarAlgoritmos: () => pedir("/algoritmos"),

    // Componentes
    listarComponentes: () => pedir("/components"),
    crearComponente: (comp) =>
      pedir("/components", { method: "POST", body: JSON.stringify(comp) }),
    eliminarComponente: (id) =>
      pedir("/components/" + encodeURIComponent(id), { method: "DELETE" }),

    // Conexiones
    listarConexiones: () => pedir("/connections"),
    crearConexion: (cx) =>
      pedir("/connections", { method: "POST", body: JSON.stringify(cx) }),

    // Trazado
    rutear: (peticion) =>
      pedir("/route", { method: "POST", body: JSON.stringify(peticion) }),

    // Historial
    deshacer: () => pedir("/undo", { method: "POST" }),
    rehacer: () => pedir("/redo", { method: "POST" }),

    // Proyecto
    obtenerProyecto: () => pedir("/project"),
    renombrar: (nombre) =>
      pedir("/project/rename", { method: "POST", body: JSON.stringify({ nombre }) }),
    limpiarProyecto: () => pedir("/project/clear", { method: "POST" }),

    // Importacion: usa FormData en lugar de JSON
    importar: async (archivo) => {
      const fd = new FormData();
      fd.append("archivo", archivo);
      const resp = await fetch(BASE + "/import", { method: "POST", body: fd });
      if (!resp.ok) {
        const j = await resp.json().catch(() => ({}));
        throw new Error(j.detail || "Error al importar");
      }
      return resp.json();
    },

    // Las exportaciones devuelven archivos: construimos URLs de descarga directa
    urlExportJson: () => BASE + "/export/json",
    urlExportCsv: () => BASE + "/export/csv",
    urlExportImagen: (oscuro, pcb) =>
      BASE + "/export/image?modo_oscuro=" + (oscuro ? "true" : "false") +
      "&modo_pcb=" + (pcb ? "true" : "false"),
    urlExportPdf: (pcb) => BASE + "/export/pdf?modo_pcb=" + (pcb ? "true" : "false"),
  };
})();
