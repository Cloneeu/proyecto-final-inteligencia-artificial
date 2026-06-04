"""
Modelos de datos del sistema usando Pydantic.

Definen la forma de los componentes, las conexiones y las peticiones que
recibe la API. Pydantic valida automaticamente los tipos y rangos.
"""

from typing import List, Optional, Tuple
from pydantic import BaseModel, Field


# Tipos de componente aceptados. Se mantiene abierto con un valor "otro"
# para no rechazar piezas que no esten en la lista.
TIPOS_COMPONENTE = [
    "resistencia", "capacitor", "led", "microcontrolador",
    "diodo", "transistor", "conector", "integrado", "otro",
]


class Componente(BaseModel):
    """Componente electronico colocado sobre la placa."""
    id: str = Field(..., description="Identificador unico, por ejemplo R1 o LED1")
    nombre: str = Field(..., description="Nombre descriptivo del componente")
    tipo: str = Field(default="otro", description="Tipo de componente")
    x: int = Field(..., ge=0, description="Columna donde se ubica")
    y: int = Field(..., ge=0, description="Fila donde se ubica")
    ancho: int = Field(default=1, ge=1, description="Ancho en celdas")
    alto: int = Field(default=1, ge=1, description="Alto en celdas")
    color: str = Field(default="#3b82f6", description="Color identificador en hex")
    pines: int = Field(
        default=2, ge=1, le=64,
        description="Numero de patitas. Solo lo usan micro/integrado/conector; "
                    "los demas tipos tienen un numero fijo por su simbolo."
    )


class Conexion(BaseModel):
    """
    Conexion (net) entre dos patitas. source/target dicen a que componente
    pertenece cada patita, y pin_origen/pin_destino el indice de la patita.
    """
    source: str = Field(..., description="ID del componente origen")
    target: str = Field(..., description="ID del componente destino")
    pin_origen: int = Field(default=0, ge=0, description="Indice de la patita origen")
    pin_destino: int = Field(default=0, ge=0, description="Indice de la patita destino")


class ConfiguracionPlaca(BaseModel):
    """Dimensiones de la cuadricula del PCB."""
    filas: int = Field(default=30, ge=2, le=1000)
    columnas: int = Field(default=30, ge=2, le=1000)
    tamano_celda: int = Field(default=20, ge=4, le=80,
                              description="Tamano visual de la celda en pixeles")


class PeticionRuteo(BaseModel):
    """Peticion para trazar todas las conexiones con un algoritmo dado."""
    algoritmo: str = Field(default="astar", description="astar, dijkstra o bfs")
    evitar_pistas: bool = Field(
        default=True,
        description="Si es True, las pistas ya trazadas se tratan como obstaculos"
    )
    permitir_diagonales: bool = Field(
        default=False,
        description="Si es True, el trazado puede moverse en diagonal (45 grados)"
    )


class ResultadoRuta(BaseModel):
    """Resultado del trazado de una conexion concreta."""
    source: str
    target: str
    exito: bool
    camino: List[Tuple[int, int]] = []
    longitud: int = 0
    nodos_explorados: int = 0
    tiempo_ms: float = 0.0
    color: str = "#22c55e"
    mensaje: str = ""


class Proyecto(BaseModel):
    """Estado completo de un proyecto, util para guardar y abrir."""
    nombre: str = Field(default="proyecto_sin_nombre")
    placa: ConfiguracionPlaca = ConfiguracionPlaca()
    componentes: List[Componente] = []
    conexiones: List[Conexion] = []
