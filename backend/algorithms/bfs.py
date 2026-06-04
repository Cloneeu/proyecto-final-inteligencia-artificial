

import time
from collections import deque
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
    """
    Ejecuta BFS y devuelve el mismo formato de resultado que A* y Dijkstra.

    Nota: BFS trata cada vecino como un solo paso. Con diagonales activadas
    minimiza el numero de pasos, no la longitud real de la pista, por lo que
    puede dar un camino algo mas largo que A* o Dijkstra.
    """
    t0 = time.perf_counter()

    cola = deque([inicio])
    visitados = {inicio}
    origen_de: Dict[Tuple[int, int], Tuple[int, int]] = {}
    nodos_explorados = 0

    while cola:
        actual = cola.popleft()
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
                "mensaje": "Ruta encontrada con BFS",
            }

        for nx, ny, _coste in cuadricula.vecinos(
                actual[0], actual[1], evitar_pistas, permitir_diagonales):
            vecino = (nx, ny)
            if vecino not in visitados:
                visitados.add(vecino)
                origen_de[vecino] = actual
                cola.append(vecino)

    t1 = time.perf_counter()
    return {
        "exito": False,
        "camino": [],
        "longitud": 0,
        "nodos_explorados": nodos_explorados,
        "tiempo_ms": round((t1 - t0) * 1000, 3),
        "mensaje": "No existe ruta posible entre origen y destino",
    }
