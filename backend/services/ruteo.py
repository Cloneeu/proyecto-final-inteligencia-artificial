

from typing import List, Tuple, Dict

from algorithms import resolver
from algorithms.grid import Cuadricula, CELDA_LIBRE, CELDA_OCUPADA
from models.schemas import Componente, Conexion, ResultadoRuta


# Paleta de colores para diferenciar pistas en la visualizacion
_PALETA = [
    "#22c55e", "#f59e0b", "#ef4444", "#8b5cf6",
    "#06b6d4", "#ec4899", "#84cc16", "#f97316",
]


def pines_de(comp: Componente) -> List[Tuple[int, int]]:
    """
    Devuelve la celda de ruteo de cada patita del componente, en orden de indice.

    Las celdas quedan JUSTO AFUERA del borde del componente para que la pista
    salga limpia y funcione incluso con componentes de 1x1. Esta misma regla se
    replica en el frontend (canvas.js) para que dibujo y ruteo coincidan.
    """
    x, y, w, h = comp.x, comp.y, comp.ancho, comp.alto
    mid_y = y + h // 2
    mid_x = x + w // 2
    tipo = comp.tipo

    if tipo == "transistor":
        # base a la izquierda, colector arriba-derecha, emisor abajo-derecha.
        # max(1, h-1) evita que colector y emisor caigan en la misma celda si h=1.
        return [(x - 1, mid_y), (x + w, y), (x + w, y + max(1, h - 1))]

    if tipo in ("microcontrolador", "integrado"):
        # pines repartidos en los dos lados, estilo DIP
        n = max(2, comp.pines)
        k = (n + 1) // 2          # mitad (o una mas) en el lado izquierdo
        celdas = []
        for i in range(k):        # lado izquierdo, arriba -> abajo
            fila = y + min(h - 1, int((i + 0.5) * h / k))
            celdas.append((x - 1, fila))
        der = n - k
        for i in range(der):      # lado derecho, arriba -> abajo
            fila = y + min(h - 1, int((i + 0.5) * h / der))
            celdas.append((x + w, fila))
        return celdas

    if tipo == "conector":
        # pines en una fila debajo del componente
        n = max(2, comp.pines)
        celdas = []
        for i in range(n):
            col = x + min(w - 1, int((i + 0.5) * w / n))
            celdas.append((col, y + h))
        return celdas

    # resistencia, capacitor, diodo, led y "otro": 2 patitas izquierda/derecha
    return [(x - 1, mid_y), (x + w, mid_y)]


def _celda_en_placa(celda: Tuple[int, int], grid: Cuadricula) -> Tuple[int, int]:
    """Recorta una celda para que quede dentro de la placa (por si un pin cae fuera)."""
    cx = max(0, min(grid.columnas - 1, celda[0]))
    cy = max(0, min(grid.filas - 1, celda[1]))
    return cx, cy


def construir_cuadricula(filas: int, columnas: int,
                         componentes: List[Componente]) -> Cuadricula:
    grid = Cuadricula(filas, columnas)
    for comp in componentes:
        grid.marcar_area_ocupada(comp.x, comp.y, comp.ancho, comp.alto)
    return grid


def trazar_conexiones(filas: int, columnas: int,
                      componentes: List[Componente],
                      conexiones: List[Conexion],
                      algoritmo: str = "astar",
                      evitar_pistas: bool = True,
                      permitir_diagonales: bool = False) -> Dict:

    grid = construir_cuadricula(filas, columnas, componentes)
    indice = {c.id: c for c in componentes}

    # Todas las celdas de patita de todos los componentes. Se calculan una sola
    # vez porque no cambian entre conexiones. Al trazar cada pista las bloqueamos
    # (menos las dos patitas extremo) para que ninguna pista pase sobre una patita
    # ajena.
    todas_las_patitas = set()
    for comp in componentes:
        for celda in pines_de(comp):
            todas_las_patitas.add(_celda_en_placa(celda, grid))

    resultados: List[ResultadoRuta] = []
    advertencias: List[str] = []

    longitudes = []
    tiempos = []
    completadas = 0

    for i, conexion in enumerate(conexiones):
        origen = indice.get(conexion.source)
        destino = indice.get(conexion.target)

        # Validacion: ambos componentes deben existir
        if origen is None or destino is None:
            faltante = conexion.source if origen is None else conexion.target
            resultados.append(ResultadoRuta(
                source=conexion.source, target=conexion.target,
                exito=False, mensaje=f"Componente '{faltante}' no existe",
            ))
            advertencias.append(
                f"Conexion {conexion.source}->{conexion.target}: "
                f"componente '{faltante}' inexistente"
            )
            continue

        # Tomamos la celda de cada patita elegida (validando el indice)
        pines_origen = pines_de(origen)
        pines_destino = pines_de(destino)
        if (conexion.pin_origen >= len(pines_origen) or
                conexion.pin_destino >= len(pines_destino)):
            resultados.append(ResultadoRuta(
                source=conexion.source, target=conexion.target,
                exito=False, mensaje="Patita inexistente en el componente",
            ))
            advertencias.append(
                f"Conexion {conexion.source}.{conexion.pin_origen}->"
                f"{conexion.target}.{conexion.pin_destino}: patita inexistente"
            )
            continue

        inicio = _celda_en_placa(pines_origen[conexion.pin_origen], grid)
        fin = _celda_en_placa(pines_destino[conexion.pin_destino], grid)

        # Preparamos la cuadricula para esta conexion:
        #  - bloqueamos todas las patitas ajenas (para que la pista no pase sobre
        #    el punto de conexion de otro componente),
        #  - liberamos las dos patitas extremo (inicio y fin) para poder salir/llegar.
        respaldo = {}
        for (cx, cy) in todas_las_patitas - {inicio, fin}:
            respaldo[(cx, cy)] = grid.celdas[cy][cx]
            grid.celdas[cy][cx] = CELDA_OCUPADA
        for (cx, cy) in (inicio, fin):
            if (cx, cy) not in respaldo:
                respaldo[(cx, cy)] = grid.celdas[cy][cx]
            grid.celdas[cy][cx] = CELDA_LIBRE

        res = resolver(algoritmo, grid, inicio, fin, evitar_pistas,
                       permitir_diagonales)

        # Restauramos los valores originales de las celdas liberadas
        for (cx, cy), valor in respaldo.items():
            grid.celdas[cy][cx] = valor

        color = _PALETA[i % len(_PALETA)]

        if res["exito"]:
            completadas += 1
            longitudes.append(res["longitud"])
            tiempos.append(res["tiempo_ms"])
            # Marcamos la pista en la cuadricula (sin tocar inicio ni fin)
            for (px, py) in res["camino"][1:-1]:
                grid.marcar_pista(px, py)
        else:
            advertencias.append(
                f"Conexion {conexion.source}->{conexion.target}: {res['mensaje']}"
            )

        resultados.append(ResultadoRuta(
            source=conexion.source,
            target=conexion.target,
            exito=res["exito"],
            camino=res["camino"],
            longitud=res["longitud"],
            nodos_explorados=res["nodos_explorados"],
            tiempo_ms=res["tiempo_ms"],
            color=color,
            mensaje=res["mensaje"],
        ))

    # Estadisticas globales
    total = len(conexiones)
    estadisticas = {
        "componentes_totales": len(componentes),
        "conexiones_totales": total,
        "conexiones_completadas": completadas,
        "conexiones_fallidas": total - completadas,
        "longitud_promedio": round(sum(longitudes) / len(longitudes), 2)
                             if longitudes else 0,
        "longitud_total": sum(longitudes),
        "tiempo_promedio_ms": round(sum(tiempos) / len(tiempos), 3)
                              if tiempos else 0,
        "tiempo_total_ms": round(sum(tiempos), 3),
        "algoritmo": algoritmo,
    }

    return {
        "resultados": [r.model_dump() for r in resultados],
        "estadisticas": estadisticas,
        "advertencias": advertencias,
    }
