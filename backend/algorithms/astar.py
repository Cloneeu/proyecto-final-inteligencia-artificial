
import heapq
import time
from typing import List, Tuple, Optional, Dict

from .grid import Cuadricula


def distancia_manhattan(a: Tuple[int, int], b: Tuple[int, int]) -> int:
    """Heuristica para movimiento ortogonal: suma de diferencias en X e Y."""
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def distancia_octogonal(a: Tuple[int, int], b: Tuple[int, int]) -> float:
    """
    Heuristica para movimiento con diagonales (octile).
    Cuenta los pasos diagonales (coste raiz de 2) y el resto ortogonales
    (coste 1). Sigue siendo admisible, asi que A* mantiene el camino optimo.
    """
    dx = abs(a[0] - b[0])
    dy = abs(a[1] - b[1])
    return (dx + dy) + (1.4142135623730951 - 2) * min(dx, dy)


def reconstruir_camino(origen_de: Dict, actual: Tuple[int, int]
                       ) -> List[Tuple[int, int]]:
    """Reconstruye el camino siguiendo los padres desde el destino al inicio."""
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
    Ejecuta A* sobre la cuadricula.

    Devuelve un diccionario con:
      - exito: bool
      - camino: lista de coordenadas (x, y)
      - longitud: numero de pasos del camino
      - nodos_explorados: cuantas celdas se sacaron de la cola
      - tiempo_ms: tiempo de calculo en milisegundos
      - mensaje: texto descriptivo del resultado
    """
    t0 = time.perf_counter()

    # Cola de prioridad: (f, contador, nodo). El contador desempata para
    # evitar comparar tuplas de coordenadas cuando f coincide.
    cola: List = []
    contador = 0
    heapq.heappush(cola, (0, contador, inicio))

    origen_de: Dict[Tuple[int, int], Tuple[int, int]] = {}
    coste_g: Dict[Tuple[int, int], float] = {inicio: 0}
    nodos_explorados = 0

    # Elegimos la heuristica segun se permitan o no diagonales
    heuristica = distancia_octogonal if permitir_diagonales else distancia_manhattan

    while cola:
        _, _, actual = heapq.heappop(cola)
        nodos_explorados += 1

        # Llegamos al destino: reconstruimos y devolvemos
        if actual == destino:
            camino = reconstruir_camino(origen_de, actual)
            t1 = time.perf_counter()
            return {
                "exito": True,
                "camino": camino,
                "longitud": len(camino) - 1,
                "nodos_explorados": nodos_explorados,
                "tiempo_ms": round((t1 - t0) * 1000, 3),
                "mensaje": "Ruta encontrada con A*",
            }

        # Exploramos vecinos (cada uno trae su propio coste de paso)
        for nx, ny, coste in cuadricula.vecinos(
                actual[0], actual[1], evitar_pistas, permitir_diagonales):
            vecino = (nx, ny)
            nuevo_g = coste_g[actual] + coste
            if vecino not in coste_g or nuevo_g < coste_g[vecino]:
                coste_g[vecino] = nuevo_g
                f = nuevo_g + heuristica(vecino, destino)
                contador += 1
                heapq.heappush(cola, (f, contador, vecino))
                origen_de[vecino] = actual

    # Se agoto la cola sin alcanzar el destino
    t1 = time.perf_counter()
    return {
        "exito": False,
        "camino": [],
        "longitud": 0,
        "nodos_explorados": nodos_explorados,
        "tiempo_ms": round((t1 - t0) * 1000, 3),
        "mensaje": "No existe ruta posible entre origen y destino",
    }
