
import copy
from typing import List, Optional

from models.schemas import (
    Componente, Conexion, ConfiguracionPlaca, Proyecto,
)


class EstadoProyecto:
    """Contenedor del proyecto activo con soporte de undo/redo."""

    def __init__(self):
        self.placa = ConfiguracionPlaca()
        self.componentes: List[Componente] = []
        self.conexiones: List[Conexion] = []
        self.nombre = "proyecto_sin_nombre"

        # Pilas para el historial. Cada entrada es una "foto" del estado.
        self._pila_deshacer: List[dict] = []
        self._pila_rehacer: List[dict] = []
        # Guardamos el estado inicial vacio como punto de partida
        self._guardar_instantanea()

    # historial
    def _instantanea_actual(self) -> dict:
        """Crea una copia profunda del estado actual."""
        return {
            "nombre": self.nombre,
            "placa": self.placa.model_copy(deep=True),
            "componentes": copy.deepcopy(self.componentes),
            "conexiones": copy.deepcopy(self.conexiones),
        }

    def _guardar_instantanea(self) -> None:
        """Apila el estado actual en deshacer y limpia la pila de rehacer."""
        self._pila_deshacer.append(self._instantanea_actual())
        self._pila_rehacer.clear()

    def _aplicar_instantanea(self, snap: dict) -> None:
        """Restaura el estado desde una instantanea."""
        self.nombre = snap["nombre"]
        self.placa = snap["placa"].model_copy(deep=True)
        self.componentes = copy.deepcopy(snap["componentes"])
        self.conexiones = copy.deepcopy(snap["conexiones"])

    def deshacer(self) -> bool:
        """Vuelve al estado anterior. Devuelve False si no hay nada que deshacer."""
        # Necesitamos al menos dos instantaneas: la actual y la previa
        if len(self._pila_deshacer) <= 1:
            return False
        actual = self._pila_deshacer.pop()
        self._pila_rehacer.append(actual)
        self._aplicar_instantanea(self._pila_deshacer[-1])
        return True

    def rehacer(self) -> bool:
        """Reaplica un estado deshecho. Devuelve False si no hay nada que rehacer."""
        if not self._pila_rehacer:
            return False
        snap = self._pila_rehacer.pop()
        self._pila_deshacer.append(snap)
        self._aplicar_instantanea(snap)
        return True

    # placa
    def configurar_placa(self, config: ConfiguracionPlaca) -> None:
        self.placa = config
        self._guardar_instantanea()

    # componentes
    def buscar_componente(self, id_componente: str) -> Optional[Componente]:
        for c in self.componentes:
            if c.id == id_componente:
                return c
        return None

    def agregar_componente(self, comp: Componente) -> Componente:
        """Agrega o reemplaza un componente segun su ID."""
        existente = self.buscar_componente(comp.id)
        if existente:
            # Reemplazamos manteniendo la posicion en la lista
            idx = self.componentes.index(existente)
            self.componentes[idx] = comp
        else:
            self.componentes.append(comp)
        self._guardar_instantanea()
        return comp

    def eliminar_componente(self, id_componente: str) -> bool:
        comp = self.buscar_componente(id_componente)
        if not comp:
            return False
        self.componentes.remove(comp)
        # Tambien eliminamos conexiones que dependan de ese componente
        self.conexiones = [
            cx for cx in self.conexiones
            if cx.source != id_componente and cx.target != id_componente
        ]
        self._guardar_instantanea()
        return True

    # conexiones
    def agregar_conexion(self, conexion: Conexion) -> Conexion:
        self.conexiones.append(conexion)
        self._guardar_instantanea()
        return conexion

    # proyecto 
    def exportar_proyecto(self) -> Proyecto:
        return Proyecto(
            nombre=self.nombre,
            placa=self.placa,
            componentes=self.componentes,
            conexiones=self.conexiones,
        )

    def cargar_proyecto(self, proyecto: Proyecto) -> None:
        self.nombre = proyecto.nombre
        self.placa = proyecto.placa
        self.componentes = list(proyecto.componentes)
        self.conexiones = list(proyecto.conexiones)
        self._guardar_instantanea()

    def limpiar(self) -> None:
        """
        Borra todos los componentes y conexiones, pero conserva el tamano de
        la placa y el nombre. Queda registrado en el historial, asi que se
        puede revertir con Deshacer.
        """
        self.componentes = []
        self.conexiones = []
        self._guardar_instantanea()


estado = EstadoProyecto()
