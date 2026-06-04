

from typing import List, Tuple, Dict

from algorithms import resolver
from algorithms.grid import Cuadricula
from models.schemas import Componente, Conexion, ResultadoRuta


# Paleta de colores para diferenciar pistas en la visualizacion
_PALETA = [
    "#22c55e", "#f59e0b", "#ef4444", "#8b5cf6",
    "#06b6d4", "#ec4899", "#84cc16", "#f97316",
]


def _centro_componente(comp: Componente) -> Tuple[int, int]:
    """Devuelve la celda central aproximada de un componente."""
    cx = comp.x + comp.ancho // 2
    cy = comp.y + comp.alto // 2
    return cx, cy


def _celdas_componente(comp: Componente) -> List[Tuple[int, int]]:
    """Lista todas las celdas que ocupa un componente."""
    celdas = []
    for fila in range(comp.y, comp.y + comp.alto):
        for col in range(comp.x, comp.x + comp.ancho):
            celdas.append((col, fila))
    return celdas


def _celdas_a_liberar(origen: Componente, destino: Componente,
                      grid: Cuadricula) -> set:

    liberar = set()
    for comp in (origen, destino):
        for (cx, cy) in _celdas_componente(comp):
            if grid.dentro_de_limites(cx, cy):
                liberar.add((cx, cy))
            # Borde alrededor de la celda
            for dx, dy in [(0, -1), (0, 1), (-1, 0), (1, 0)]:
                nx, ny = cx + dx, cy + dy
                if grid.dentro_de_limites(nx, ny):
                    liberar.add((nx, ny))
    return liberar


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
                      evitar_pistas: bool = True) -> Dict:
   
    grid = construir_cuadricula(filas, columnas, componentes)
    indice = {c.id: c for c in componentes}

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

        inicio = _centro_componente(origen)
        fin = _centro_componente(destino)

       
        celdas_liberadas = _celdas_a_liberar(origen, destino, grid)
        respaldo = {}
        for (cx, cy) in celdas_liberadas:
            respaldo[(cx, cy)] = grid.celdas[cy][cx]
            grid.celdas[cy][cx] = 0

        res = resolver(algoritmo, grid, inicio, fin, evitar_pistas)

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
