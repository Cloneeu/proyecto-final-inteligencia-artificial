

import csv
import io
import json
from typing import List, Dict, Tuple

from PIL import Image, ImageDraw, ImageFont
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage,
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

from models.schemas import Componente, Conexion


# utilidad de color
def _hex_a_rgb(valor: str) -> Tuple[int, int, int]:
    """Convierte un color hexadecimal #rrggbb a una tupla RGB."""
    valor = valor.lstrip("#")
    if len(valor) == 3:
        valor = "".join(c * 2 for c in valor)
    try:
        return tuple(int(valor[i:i + 2], 16) for i in (0, 2, 4))
    except ValueError:
        return (59, 130, 246)  # azul por defecto si el color es invalido


# png
def generar_imagen(filas: int, columnas: int, tamano_celda: int,
                   componentes: List[Componente],
                   resultados_ruta: List[Dict],
                   modo_oscuro: bool = True) -> bytes:
    """
    Dibuja la placa completa y devuelve los bytes PNG.
    Incluye la cuadricula, los componentes y las pistas trazadas.
    """
    margen = 20
    ancho = columnas * tamano_celda + margen * 2
    alto = filas * tamano_celda + margen * 2

    fondo = (30, 30, 30) if modo_oscuro else (248, 250, 252)
    color_grid = (60, 60, 60) if modo_oscuro else (210, 215, 225)

    img = Image.new("RGB", (ancho, alto), fondo)
    dibujo = ImageDraw.Draw(img)

    # Cuadricula
    for col in range(columnas + 1):
        x = margen + col * tamano_celda
        dibujo.line([(x, margen), (x, alto - margen)], fill=color_grid, width=1)
    for fila in range(filas + 1):
        y = margen + fila * tamano_celda
        dibujo.line([(margen, y), (ancho - margen, y)], fill=color_grid, width=1)

    # Pistas (se dibujan antes que los componentes para que estos queden encima)
    for res in resultados_ruta:
        if not res.get("exito"):
            continue
        color = _hex_a_rgb(res.get("color", "#22c55e"))
        camino = res.get("camino", [])
        puntos = [
            (margen + cx * tamano_celda + tamano_celda // 2,
             margen + cy * tamano_celda + tamano_celda // 2)
            for cx, cy in camino
        ]
        if len(puntos) >= 2:
            dibujo.line(puntos, fill=color, width=max(2, tamano_celda // 6))

    # Componentes
    for comp in componentes:
        x0 = margen + comp.x * tamano_celda
        y0 = margen + comp.y * tamano_celda
        x1 = x0 + comp.ancho * tamano_celda
        y1 = y0 + comp.alto * tamano_celda
        color = _hex_a_rgb(comp.color)
        dibujo.rectangle([x0, y0, x1, y1], fill=color, outline=(255, 255, 255))
        # Etiqueta con el ID
        try:
            fuente = ImageFont.load_default()
            dibujo.text((x0 + 3, y0 + 2), comp.id, fill=(255, 255, 255), font=fuente)
        except Exception:
            pass

    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    return buffer.getvalue()


# pdf
def generar_pdf(nombre_proyecto: str,
                componentes: List[Componente],
                conexiones: List[Conexion],
                resultados_ruta: List[Dict],
                estadisticas: Dict,
                imagen_png: bytes) -> bytes:
    """Genera el reporte PDF con componentes, conexiones, estadisticas e imagen."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4,
                            topMargin=20 * mm, bottomMargin=20 * mm,
                            leftMargin=18 * mm, rightMargin=18 * mm)
    estilos = getSampleStyleSheet()
    titulo = ParagraphStyle("titulo", parent=estilos["Title"], fontSize=18)
    subtitulo = ParagraphStyle("sub", parent=estilos["Heading2"], fontSize=13)

    elementos = []
    elementos.append(Paragraph("Reporte de Trazado de PCB", titulo))
    elementos.append(Paragraph(f"Proyecto: {nombre_proyecto}", estilos["Normal"]))
    elementos.append(Spacer(1, 8))

    # Estadisticas
    elementos.append(Paragraph("Estadisticas", subtitulo))
    datos_stats = [["Metrica", "Valor"]]
    etiquetas = {
        "algoritmo": "Algoritmo usado",
        "componentes_totales": "Componentes totales",
        "conexiones_totales": "Conexiones totales",
        "conexiones_completadas": "Conexiones completadas",
        "conexiones_fallidas": "Conexiones fallidas",
        "longitud_total": "Longitud total (celdas)",
        "longitud_promedio": "Longitud promedio",
        "tiempo_total_ms": "Tiempo total (ms)",
        "tiempo_promedio_ms": "Tiempo promedio (ms)",
    }
    for clave, etiqueta in etiquetas.items():
        datos_stats.append([etiqueta, str(estadisticas.get(clave, "-"))])
    tabla_stats = Table(datos_stats, colWidths=[90 * mm, 70 * mm])
    tabla_stats.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e293b")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1),
         [colors.white, colors.HexColor("#f1f5f9")]),
    ]))
    elementos.append(tabla_stats)
    elementos.append(Spacer(1, 10))

    # Imagen de la placa
    elementos.append(Paragraph("Resultado visual", subtitulo))
    img_buffer = io.BytesIO(imagen_png)
    # Escalamos la imagen para que entre en el ancho de pagina
    elementos.append(RLImage(img_buffer, width=170 * mm, height=120 * mm,
                             kind="proportional"))
    elementos.append(Spacer(1, 10))

    # Tabla de componentes
    elementos.append(Paragraph("Componentes", subtitulo))
    datos_comp = [["ID", "Nombre", "Tipo", "X", "Y"]]
    for c in componentes:
        datos_comp.append([c.id, c.nombre, c.tipo, str(c.x), str(c.y)])
    tabla_comp = Table(datos_comp, colWidths=[25*mm, 55*mm, 40*mm, 20*mm, 20*mm])
    tabla_comp.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e293b")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
    ]))
    elementos.append(tabla_comp)
    elementos.append(Spacer(1, 10))

    # Tabla de conexiones con su resultado
    elementos.append(Paragraph("Conexiones", subtitulo))
    datos_cx = [["Origen", "Destino", "Estado", "Longitud", "Nodos", "Tiempo ms"]]
    mapa_res = {(r["source"], r["target"]): r for r in resultados_ruta}
    for cx in conexiones:
        r = mapa_res.get((cx.source, cx.target), {})
        estado = "OK" if r.get("exito") else "FALLO"
        datos_cx.append([
            cx.source, cx.target, estado,
            str(r.get("longitud", "-")),
            str(r.get("nodos_explorados", "-")),
            str(r.get("tiempo_ms", "-")),
        ])
    tabla_cx = Table(datos_cx, colWidths=[28*mm, 28*mm, 24*mm, 24*mm, 24*mm, 28*mm])
    tabla_cx.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e293b")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
    ]))
    elementos.append(tabla_cx)

    doc.build(elementos)
    return buffer.getvalue()


# json y csv
def exportar_json(proyecto_dict: Dict) -> bytes:
    """Serializa el proyecto completo a JSON."""
    return json.dumps(proyecto_dict, indent=2, ensure_ascii=False).encode("utf-8")


def exportar_csv(componentes: List[Componente],
                 conexiones: List[Conexion]) -> bytes:
    """
    Exporta componentes y conexiones a un unico CSV con dos secciones.
    La primera columna indica el tipo de fila (COMPONENTE o CONEXION).
    """
    salida = io.StringIO()
    escritor = csv.writer(salida)
    escritor.writerow(["seccion", "campo1", "campo2", "campo3",
                       "campo4", "campo5", "campo6", "campo7"])
    escritor.writerow(["#COMPONENTES", "id", "nombre", "tipo",
                       "x", "y", "ancho", "alto/color"])
    for c in componentes:
        escritor.writerow(["COMPONENTE", c.id, c.nombre, c.tipo,
                           c.x, c.y, c.ancho, c.color])
    escritor.writerow(["#CONEXIONES", "source", "target", "", "", "", "", ""])
    for cx in conexiones:
        escritor.writerow(["CONEXION", cx.source, cx.target, "", "", "", "", ""])
    return salida.getvalue().encode("utf-8")


# importacion
def importar_json(contenido: bytes) -> Dict:
    """Lee un JSON de proyecto y devuelve el diccionario."""
    return json.loads(contenido.decode("utf-8"))


def importar_csv(contenido: bytes) -> Dict:
    """
    Lee un CSV con el formato exportado por esta misma herramienta y
    reconstruye listas de componentes y conexiones.
    """
    texto = contenido.decode("utf-8")
    lector = csv.reader(io.StringIO(texto))
    componentes = []
    conexiones = []
    for fila in lector:
        if not fila:
            continue
        marca = fila[0]
        if marca == "COMPONENTE":
            componentes.append({
                "id": fila[1], "nombre": fila[2], "tipo": fila[3],
                "x": int(fila[4]), "y": int(fila[5]),
                "ancho": int(fila[6]) if fila[6] else 1,
                "color": fila[7] if len(fila) > 7 and fila[7] else "#3b82f6",
            })
        elif marca == "CONEXION":
            conexiones.append({"source": fila[1], "target": fila[2]})
    return {"componentes": componentes, "conexiones": conexiones}
