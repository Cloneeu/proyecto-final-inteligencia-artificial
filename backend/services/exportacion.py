

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
from services.ruteo import pines_de


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


# ------------------------------------------------------------------
# Dibujo de simbolos electronicos para la exportacion (espejo del canvas)
# ------------------------------------------------------------------
# Estos ayudantes replican con PIL los mismos simbolos que se ven en pantalla,
# para que la imagen exportada coincida con el esquematico del lienzo.
RAIZ2 = 1.4142135623730951


def _resistencia(d, x, y, w, h, color, g):
    """Zigzag horizontal con dos terminales."""
    cy = y + h / 2
    x0, x1 = x + w * 0.18, x + w * 0.82
    ancho = x1 - x0
    amp = h * 0.22
    picos = 6
    puntos = [(x, cy), (x0, cy)]
    for i in range(picos):
        px = x0 + ancho * (i + 0.5) / picos
        py = cy + (-amp if i % 2 == 0 else amp)
        puntos.append((px, py))
    puntos += [(x1, cy), (x + w, cy)]
    d.line(puntos, fill=color, width=g, joint="curve")


def _capacitor(d, x, y, w, h, color, g):
    """Dos placas paralelas con terminales."""
    cy = y + h / 2
    gap = w * 0.1
    xa, xb = x + w / 2 - gap, x + w / 2 + gap
    mitad = h * 0.3
    d.line([(x, cy), (xa, cy)], fill=color, width=g)
    d.line([(xb, cy), (x + w, cy)], fill=color, width=g)
    d.line([(xa, cy - mitad), (xa, cy + mitad)], fill=color, width=g)
    d.line([(xb, cy - mitad), (xb, cy + mitad)], fill=color, width=g)


def _diodo(d, x, y, w, h, color, g, es_led):
    """Triangulo + barra de catodo. Si es LED agrega flechas de luz."""
    cy = y + h / 2
    tx0, tx1 = x + w * 0.32, x + w * 0.64
    th = h * 0.28
    d.line([(x, cy), (tx0, cy)], fill=color, width=g)
    d.line([(tx1, cy), (x + w, cy)], fill=color, width=g)
    # triangulo apuntando a la derecha
    d.polygon([(tx0, cy - th), (tx0, cy + th), (tx1, cy)], outline=color, width=g)
    # barra del catodo
    d.line([(tx1, cy - th), (tx1, cy + th)], fill=color, width=g)
    if es_led:
        ax = x + w * 0.5
        d.line([(ax, cy - th), (ax + w * 0.12, cy - th - h * 0.24)],
               fill=color, width=g)
        d.line([(ax + w * 0.14, cy - th), (ax + w * 0.26, cy - th - h * 0.24)],
               fill=color, width=g)


def _transistor(d, x, y, w, h, color, g):
    """Circulo con base, colector y emisor."""
    cx, cy = x + w / 2, y + h / 2
    r = min(w, h) * 0.32
    d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=color, width=g)
    bx = cx - r * 0.35
    d.line([(x, cy), (bx, cy)], fill=color, width=g)
    d.line([(bx, cy - r * 0.6), (bx, cy + r * 0.6)], fill=color, width=g)
    d.line([(bx, cy - r * 0.25), (cx + r * 0.5, cy - r * 0.6),
            (cx + r * 0.5, y)], fill=color, width=g, joint="curve")
    d.line([(bx, cy + r * 0.25), (cx + r * 0.5, cy + r * 0.6),
            (cx + r * 0.5, y + h)], fill=color, width=g, joint="curve")


def _chip(d, x, y, w, h, color, g, oscuro):
    """Cuerpo del chip con patitas y punto del pin 1 (micro/integrado)."""
    m = min(w, h) * 0.18
    bx, by, bw, bh = x + m, y + m, w - 2 * m, h - 2 * m
    cuerpo = (55, 65, 81) if oscuro else (71, 85, 105)
    d.rectangle([bx, by, bx + bw, by + bh], fill=cuerpo, outline=color, width=g)
    pin_color = (203, 213, 225) if oscuro else (51, 65, 85)
    pines = max(2, int(bh / (m * 1.4)))
    for i in range(pines):
        py = by + bh * (i + 0.5) / pines
        d.line([(x, py), (bx, py)], fill=pin_color, width=g)
        d.line([(bx + bw, py), (x + w, py)], fill=pin_color, width=g)
    # punto indicador del pin 1
    rp = max(1.5, m * 0.28)
    px, py = bx + m * 0.7, by + m * 0.7
    d.ellipse([px - rp, py - rp, px + rp, py + rp], fill=color)


def _conector(d, x, y, w, h, color, g, oscuro):
    """Cuerpo con una fila de pines."""
    m = min(w, h) * 0.18
    relleno = (31, 41, 51) if oscuro else (229, 231, 235)
    d.rectangle([x + m, y + m, x + w - m, y + h - m],
                fill=relleno, outline=color, width=g)
    ancho = w - 2 * m
    pines = max(2, int(ancho / (m * 1.6)))
    cy = y + h / 2
    for i in range(pines):
        px = x + m + ancho * (i + 0.5) / pines
        rp = max(1.5, m * 0.3)
        d.ellipse([px - rp, cy - rp, px + rp, cy + rp], fill=color)


def _generico(d, x, y, w, h, color, oscuro):
    """Rectangulo de color (tipo 'otro')."""
    borde = (255, 255, 255) if oscuro else (31, 41, 51)
    d.rectangle([x, y, x + w, y + h], fill=color, outline=borde)


def _dibujar_simbolo(d, comp, x, y, w, h, g, fuente, oscuro):
    """Elige y dibuja el simbolo segun el tipo del componente."""
    color = _hex_a_rgb(comp.color)
    tipo = comp.tipo
    if tipo == "resistencia":
        _resistencia(d, x, y, w, h, color, g)
    elif tipo == "capacitor":
        _capacitor(d, x, y, w, h, color, g)
    elif tipo == "led":
        _diodo(d, x, y, w, h, color, g, True)
    elif tipo == "diodo":
        _diodo(d, x, y, w, h, color, g, False)
    elif tipo == "transistor":
        _transistor(d, x, y, w, h, color, g)
    elif tipo == "conector":
        _conector(d, x, y, w, h, color, g, oscuro)
    elif tipo in ("microcontrolador", "integrado"):
        _chip(d, x, y, w, h, color, g, oscuro)
    else:
        _generico(d, x, y, w, h, color, oscuro)
    # Etiqueta con el ID
    if fuente is not None:
        texto = (229, 231, 235) if oscuro else (31, 41, 51)
        d.text((x + 3, y + 2), comp.id, fill=texto, font=fuente)


def _dibujar_footprint(d, comp, x, y, w, h, tamano_celda, fuente):
    """Contorno de serigrafia para la vista PCB (los pads se dibujan en las patitas)."""
    blanco = (232, 238, 242)
    d.rectangle([x + 2, y + 2, x + w - 2, y + h - 2], outline=blanco,
                width=max(1, tamano_celda // 12))
    if fuente is not None:
        d.text((x + 3, y + 2), comp.id, fill=blanco, font=fuente)


def _dibujar_pines(d, comp, margen, tamano_celda, color, radio_factor):
    """Dibuja un punto por cada patita en su celda de ruteo (espejo del canvas)."""
    for (cx, cy) in pines_de(comp):
        px = margen + cx * tamano_celda + tamano_celda // 2
        py = margen + cy * tamano_celda + tamano_celda // 2
        r = max(2, int(tamano_celda * radio_factor))
        d.ellipse([px - r, py - r, px + r, py + r], fill=color)


# png
def generar_imagen(filas: int, columnas: int, tamano_celda: int,
                   componentes: List[Componente],
                   resultados_ruta: List[Dict],
                   modo_oscuro: bool = True,
                   modo_pcb: bool = False) -> bytes:
    """
    Dibuja la placa completa y devuelve los bytes PNG.
    Incluye la cuadricula, los componentes (como simbolos electronicos) y las
    pistas. Si `modo_pcb` es True, dibuja la placa real: fondo verde, pistas de
    cobre y pads dorados con serigrafia.
    """
    margen = 20
    ancho = columnas * tamano_celda + margen * 2
    alto = filas * tamano_celda + margen * 2

    if modo_pcb:
        fondo = (11, 110, 61)        # verde mascara de soldadura
    else:
        fondo = (30, 30, 30) if modo_oscuro else (248, 250, 252)
    color_grid = (60, 60, 60) if modo_oscuro else (210, 215, 225)

    img = Image.new("RGB", (ancho, alto), fondo)
    dibujo = ImageDraw.Draw(img)

    # Cuadricula (se oculta en modo PCB)
    if not modo_pcb:
        for col in range(columnas + 1):
            x = margen + col * tamano_celda
            dibujo.line([(x, margen), (x, alto - margen)], fill=color_grid, width=1)
        for fila in range(filas + 1):
            y = margen + fila * tamano_celda
            dibujo.line([(margen, y), (ancho - margen, y)], fill=color_grid, width=1)

    # Pistas (antes que los componentes para que estos queden encima)
    for res in resultados_ruta:
        if not res.get("exito"):
            continue
        if modo_pcb:
            color = (217, 164, 65)               # cobre
            grosor_pista = max(3, tamano_celda // 3)
        else:
            color = _hex_a_rgb(res.get("color", "#22c55e"))
            grosor_pista = max(2, tamano_celda // 6)
        camino = res.get("camino", [])
        puntos = [
            (margen + cx * tamano_celda + tamano_celda // 2,
             margen + cy * tamano_celda + tamano_celda // 2)
            for cx, cy in camino
        ]
        if len(puntos) >= 2:
            dibujo.line(puntos, fill=color, width=grosor_pista, joint="curve")

    # Componentes
    try:
        fuente = ImageFont.load_default()
    except Exception:
        fuente = None
    grosor = max(2, int(tamano_celda * 0.12))
    for comp in componentes:
        x0 = margen + comp.x * tamano_celda
        y0 = margen + comp.y * tamano_celda
        w = comp.ancho * tamano_celda
        h = comp.alto * tamano_celda
        if modo_pcb:
            _dibujar_footprint(dibujo, comp, x0, y0, w, h, tamano_celda, fuente)
            # pads dorados sobre las patitas
            _dibujar_pines(dibujo, comp, margen, tamano_celda, (217, 164, 65), 0.28)
        else:
            _dibujar_simbolo(dibujo, comp, x0, y0, w, h, grosor, fuente, modo_oscuro)
            # puntos de las patitas, del color del componente
            _dibujar_pines(dibujo, comp, margen, tamano_celda,
                           _hex_a_rgb(comp.color), 0.16)

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
                       "campo4", "campo5", "campo6", "campo7", "campo8"])
    escritor.writerow(["#COMPONENTES", "id", "nombre", "tipo",
                       "x", "y", "ancho", "color", "pines"])
    for c in componentes:
        escritor.writerow(["COMPONENTE", c.id, c.nombre, c.tipo,
                           c.x, c.y, c.ancho, c.color, c.pines])
    escritor.writerow(["#CONEXIONES", "source", "target",
                       "pin_origen", "pin_destino", "", "", "", ""])
    for cx in conexiones:
        escritor.writerow(["CONEXION", cx.source, cx.target,
                           cx.pin_origen, cx.pin_destino, "", "", "", ""])
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
                # 'pines' es nuevo: si el CSV es viejo y no lo trae, usamos 2
                "pines": int(fila[8]) if len(fila) > 8 and fila[8] else 2,
            })
        elif marca == "CONEXION":
            # pin_origen/pin_destino son nuevos: respaldo a 0 si faltan
            conexiones.append({
                "source": fila[1], "target": fila[2],
                "pin_origen": int(fila[3]) if len(fila) > 3 and fila[3] else 0,
                "pin_destino": int(fila[4]) if len(fila) > 4 and fila[4] else 0,
            })
    return {"componentes": componentes, "conexiones": conexiones}
