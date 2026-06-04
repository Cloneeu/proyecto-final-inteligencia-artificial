"""
Paquete de algoritmos de trazado.

Expone una funcion unica `resolver` que selecciona el algoritmo segun el nombre
recibido desde la interfaz, para que el resto del backend no dependa de los
detalles de cada implementacion.
"""

from .grid import Cuadricula
from . import astar, dijkstra, bfs

# Mapa de nombre -> modulo del algoritmo
_ALGORITMOS = {
    "astar": astar,
    "dijkstra": dijkstra,
    "bfs": bfs,
}


def algoritmos_disponibles():
    """Devuelve la lista de nombres de algoritmo aceptados."""
    return list(_ALGORITMOS.keys())


def resolver(nombre: str, cuadricula, inicio, destino, evitar_pistas=True,
             permitir_diagonales=False):
    """
    Ejecuta el algoritmo indicado.

    Lanza ValueError si el nombre no corresponde a ningun algoritmo conocido.
    """
    clave = (nombre or "astar").lower()
    if clave not in _ALGORITMOS:
        raise ValueError(
            f"Algoritmo desconocido '{nombre}'. "
            f"Use uno de: {', '.join(_ALGORITMOS.keys())}"
        )
    return _ALGORITMOS[clave].buscar(
        cuadricula, inicio, destino, evitar_pistas, permitir_diagonales)
