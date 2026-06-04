

import heapq
import time
from typing import List, Tuple, Dict

from .grid import Cuadricula


def reconstruir_camino(origen_de: Dict, actual: Tuple[int, int]
                       ) -> List[Tuple[int, int]]:
    """Reconstruye el camino siguiendo los padres."""
    camino = [actual]
    while actual in origen_de:
        actual = origen_de[actual]
        camino.append(actual)
    camino.reverse()
    return camino


def buscar(cuadricula: Cuadricula,
           inicio: Tuple[int, int],
           destino: Tuple[int, int],
           evitar_pistas: bool = True,
           permitir_diagonales: bool = False) -> dict:
    """Ejecuta Dijkstra y devuelve el mismo formato de resultado que A*."""
    t0 = time.perf_counter()

    cola: List = []
    contador = 0
    heapq.heappush(cola, (0, contador, inicio))

    origen_de: Dict[Tuple[int, int], Tuple[int, int]] = {}
    coste_g: Dict[Tuple[int, int], float] = {inicio: 0}
    nodos_explorados = 0

    while cola:
        coste_actual, _, actual = heapq.heappop(cola)
        nodos_explorados += 1

        if actual == destino:
            camino = reconstruir_camino(origen_de, actual)
            t1 = time.perf_counter()
            return {
                "exito": True,
                "camino": camino,
                "longitud": len(camino) - 1,
                "nodos_explorados": nodos_explorados,
                "tiempo_ms": round((t1 - t0) * 1000, 3),
                "mensaje": "Ruta encontrada con Dijkstra",
            }

        for nx, ny, coste in cuadricula.vecinos(
                actual[0], actual[1], evitar_pistas, permitir_diagonales):
            vecino = (nx, ny)
            nuevo_g = coste_g[actual] + coste
            if vecino not in coste_g or nuevo_g < coste_g[vecino]:
                coste_g[vecino] = nuevo_g
                contador += 1
                # La prioridad es solo el coste real, sin heuristica
                heapq.heappush(cola, (nuevo_g, contador, vecino))
                origen_de[vecino] = actual

    t1 = time.perf_counter()
    return {
        "exito": False,
        "camino": [],
        "longitud": 0,
        "nodos_explorados": nodos_explorados,
        "tiempo_ms": round((t1 - t0) * 1000, 3),
        "mensaje": "No existe ruta posible entre origen y destino",
    }
