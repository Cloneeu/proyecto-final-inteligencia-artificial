
from fastapi import APIRouter, HTTPException, UploadFile, File
from fastapi.responses import Response

from models.schemas import (
    Componente, Conexion, ConfiguracionPlaca, PeticionRuteo, Proyecto,
)
from services.estado import estado
from services import ruteo, exportacion
from algorithms import algoritmos_disponibles

router = APIRouter()

# Guardamos el ultimo resultado de ruteo para poder exportarlo en PDF/PNG
_ultimo_ruteo = {"resultados": [], "estadisticas": {}, "advertencias": []}


# placa
@router.get("/algoritmos")
def listar_algoritmos():
    """Devuelve los algoritmos de trazado disponibles."""
    return {"algoritmos": algoritmos_disponibles()}


@router.get("/placa")
def obtener_placa():
    return estado.placa


@router.post("/placa")
def configurar_placa(config: ConfiguracionPlaca):
    estado.configurar_placa(config)
    return {"mensaje": "Placa configurada", "placa": estado.placa}

#componentes
@router.get("/components")
def listar_componentes():
    return estado.componentes


@router.post("/components")
def crear_componente(comp: Componente):
    # Validamos que la posicion este dentro de la placa
    if comp.x >= estado.placa.columnas or comp.y >= estado.placa.filas:
        raise HTTPException(
            status_code=400,
            detail="El componente queda fuera de los limites de la placa",
        )
    estado.agregar_componente(comp)
    return {"mensaje": "Componente agregado", "componente": comp}


@router.delete("/components/{id_componente}")
def eliminar_componente(id_componente: str):
    if not estado.eliminar_componente(id_componente):
        raise HTTPException(status_code=404, detail="Componente no encontrado")
    return {"mensaje": f"Componente {id_componente} eliminado"}

#conexiones
@router.get("/connections")
def listar_conexiones():
    return estado.conexiones


@router.post("/connections")
def crear_conexion(conexion: Conexion):
    # Validamos que ambos componentes existan
    if not estado.buscar_componente(conexion.source):
        raise HTTPException(status_code=400,
                            detail=f"Origen '{conexion.source}' no existe")
    if not estado.buscar_componente(conexion.target):
        raise HTTPException(status_code=400,
                            detail=f"Destino '{conexion.target}' no existe")
    estado.agregar_conexion(conexion)
    return {"mensaje": "Conexion agregada", "conexion": conexion}


#trazado
@router.post("/route")
def trazar(peticion: PeticionRuteo):
    """Traza todas las conexiones con el algoritmo elegido."""
    global _ultimo_ruteo
    resultado = ruteo.trazar_conexiones(
        filas=estado.placa.filas,
        columnas=estado.placa.columnas,
        componentes=estado.componentes,
        conexiones=estado.conexiones,
        algoritmo=peticion.algoritmo,
        evitar_pistas=peticion.evitar_pistas,
        permitir_diagonales=peticion.permitir_diagonales,
    )
    _ultimo_ruteo = resultado
    return resultado

#historial
@router.post("/undo")
def deshacer():
    if not estado.deshacer():
        raise HTTPException(status_code=400, detail="No hay nada que deshacer")
    return estado.exportar_proyecto()


@router.post("/redo")
def rehacer():
    if not estado.rehacer():
        raise HTTPException(status_code=400, detail="No hay nada que rehacer")
    return estado.exportar_proyecto()


#proyecto
@router.get("/project")
def obtener_proyecto():
    return estado.exportar_proyecto()


@router.post("/project")
def cargar_proyecto(proyecto: Proyecto):
    estado.cargar_proyecto(proyecto)
    return {"mensaje": "Proyecto cargado", "proyecto": estado.exportar_proyecto()}


@router.post("/project/clear")
def borrar_todo():
    """Borra componentes, conexiones y el ultimo ruteo. Conserva la placa."""
    global _ultimo_ruteo
    estado.limpiar()
    _ultimo_ruteo = {"resultados": [], "estadisticas": {}, "advertencias": []}
    return estado.exportar_proyecto()


@router.post("/project/rename")
def renombrar_proyecto(datos: dict):
    nombre = datos.get("nombre", "").strip()
    if not nombre:
        raise HTTPException(status_code=400, detail="Nombre invalido")
    estado.nombre = nombre
    return {"mensaje": "Proyecto renombrado", "nombre": nombre}


#importacion
@router.post("/import")
async def importar(archivo: UploadFile = File(...)):
    """Importa un proyecto desde JSON o CSV."""
    contenido = await archivo.read()
    nombre = (archivo.filename or "").lower()

    try:
        if nombre.endswith(".json"):
            datos = exportacion.importar_json(contenido)
        elif nombre.endswith(".csv"):
            datos = exportacion.importar_csv(contenido)
        else:
            raise HTTPException(status_code=400,
                                detail="Formato no soportado, use JSON o CSV")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400,
                            detail=f"Error al leer el archivo: {e}")

    # Reconstruimos el proyecto
    placa = datos.get("placa", estado.placa.model_dump())
    proyecto = Proyecto(
        nombre=datos.get("nombre", estado.nombre),
        placa=ConfiguracionPlaca(**placa) if isinstance(placa, dict) else estado.placa,
        componentes=[Componente(**c) for c in datos.get("componentes", [])],
        conexiones=[Conexion(**cx) for cx in datos.get("conexiones", [])],
    )
    estado.cargar_proyecto(proyecto)
    return {"mensaje": "Importacion completada",
            "proyecto": estado.exportar_proyecto()}


#exportacion
@router.get("/export/json")
def exportar_json():
    datos = exportacion.exportar_json(estado.exportar_proyecto().model_dump())
    return Response(
        content=datos, media_type="application/json",
        headers={"Content-Disposition":
                 f'attachment; filename="{estado.nombre}.json"'},
    )


@router.get("/export/csv")
def exportar_csv():
    datos = exportacion.exportar_csv(estado.componentes, estado.conexiones)
    return Response(
        content=datos, media_type="text/csv",
        headers={"Content-Disposition":
                 f'attachment; filename="{estado.nombre}.csv"'},
    )


@router.get("/export/image")
def exportar_imagen(modo_oscuro: bool = True, modo_pcb: bool = False):
    png = exportacion.generar_imagen(
        filas=estado.placa.filas, columnas=estado.placa.columnas,
        tamano_celda=estado.placa.tamano_celda,
        componentes=estado.componentes,
        resultados_ruta=_ultimo_ruteo["resultados"],
        modo_oscuro=modo_oscuro,
        modo_pcb=modo_pcb,
    )
    return Response(
        content=png, media_type="image/png",
        headers={"Content-Disposition":
                 f'attachment; filename="{estado.nombre}.png"'},
    )


@router.get("/export/pdf")
def exportar_pdf(modo_pcb: bool = False):
    png = exportacion.generar_imagen(
        filas=estado.placa.filas, columnas=estado.placa.columnas,
        tamano_celda=estado.placa.tamano_celda,
        componentes=estado.componentes,
        resultados_ruta=_ultimo_ruteo["resultados"],
        modo_oscuro=False,
        modo_pcb=modo_pcb,
    )
    pdf = exportacion.generar_pdf(
        nombre_proyecto=estado.nombre,
        componentes=estado.componentes,
        conexiones=estado.conexiones,
        resultados_ruta=_ultimo_ruteo["resultados"],
        estadisticas=_ultimo_ruteo["estadisticas"],
        imagen_png=png,
    )
    return Response(
        content=pdf, media_type="application/pdf",
        headers={"Content-Disposition":
                 f'attachment; filename="{estado.nombre}.pdf"'},
    )
