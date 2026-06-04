
from typing import List, Tuple, Iterator

# Valores que puede tomar una celda
CELDA_LIBRE = 0
CELDA_OCUPADA = 1
CELDA_PISTA = 2


class Cuadricula:
    """Matriz 2D que modela la superficie del circuito impreso."""

    def __init__(self, filas: int, columnas: int):
        # Validacion basica de dimensiones
        if filas <= 0 or columnas <= 0:
            raise ValueError("Las filas y columnas deben ser mayores que cero")

        self.filas = filas
        self.columnas = columnas
        # Inicializamos todas las celdas como libres
        self.celdas: List[List[int]] = [
            [CELDA_LIBRE for _ in range(columnas)] for _ in range(filas)
        ]

    # ------------------------------------------------------------------
    # Consultas sobre celdas
    # ------------------------------------------------------------------
    def dentro_de_limites(self, x: int, y: int) -> bool:
        """Indica si la coordenada (x=columna, y=fila) cae dentro de la placa."""
        return 0 <= x < self.columnas and 0 <= y < self.filas

    def es_transitable(self, x: int, y: int, evitar_pistas: bool = True) -> bool:
        """
        Indica si se puede pasar por la celda.
        Por defecto las pistas ya trazadas tambien se evitan para no cruzarlas.
        """
        if not self.dentro_de_limites(x, y):
            return False
        valor = self.celdas[y][x]
        if valor == CELDA_OCUPADA:
            return False
        if valor == CELDA_PISTA and evitar_pistas:
            return False
        return True

    # ------------------------------------------------------------------
    # Modificacion de celdas
    # ------------------------------------------------------------------
    def marcar_obstaculo(self, x: int, y: int) -> None:
        """Marca una celda como ocupada por un componente."""
        if self.dentro_de_limites(x, y):
            self.celdas[y][x] = CELDA_OCUPADA

    def marcar_pista(self, x: int, y: int) -> None:
        """Marca una celda como atravesada por una pista ya trazada."""
        if self.dentro_de_limites(x, y) and self.celdas[y][x] == CELDA_LIBRE:
            self.celdas[y][x] = CELDA_PISTA

    def marcar_area_ocupada(self, x: int, y: int, ancho: int, alto: int) -> None:
        """
        Marca un area rectangular como ocupada.
        Se usa para componentes que ocupan mas de una celda.
        """
        for fila in range(y, y + alto):
            for col in range(x, x + ancho):
                self.marcar_obstaculo(col, fila)

    # ------------------------------------------------------------------
    # Vecinos
    # ------------------------------------------------------------------
    def vecinos(self, x: int, y: int, evitar_pistas: bool = True
                ) -> Iterator[Tuple[int, int]]:
        """
        Devuelve las celdas vecinas transitables.
        Se usa movimiento ortogonal (arriba, abajo, izquierda, derecha)
        porque en PCB las pistas suelen trazarse en angulos rectos.
        """
        movimientos = [(0, -1), (0, 1), (-1, 0), (1, 0)]
        for dx, dy in movimientos:
            nx, ny = x + dx, y + dy
            if self.es_transitable(nx, ny, evitar_pistas):
                yield nx, ny

    def clonar_estado(self) -> List[List[int]]:
        """Devuelve una copia de la matriz, util para depuracion o exportacion."""
        return [fila[:] for fila in self.celdas]
