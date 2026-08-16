"""Interfaz común de los proveedores de tasas."""

from __future__ import annotations

import abc
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class TasasVigentes:
    """Tasas leídas de la fuente.

    `valores` son tasas sueltas por nombre de columna (fuente antigua).
    `tablas` son tablas de tramos por monto (fuente actual); el motor usa
    éstas cuando la operación declara una `tabla`.
    """

    valores: dict[str, float]
    fecha: str | None = None
    fuente: str = "desconocida"
    obtenido_en: datetime = field(default_factory=datetime.now)
    tablas: dict[str, Any] = field(default_factory=dict)

    def get(self, columna: str) -> float:
        if columna not in self.valores:
            raise KeyError(
                f"La fuente '{self.fuente}' no trae la columna '{columna}'. "
                f"Columnas disponibles: {sorted(self.valores)}"
            )
        return self.valores[columna]


class ProveedorDeTasas(abc.ABC):
    """Fuente de tasas. Implementaciones: Sheet, Odoo, Manual."""

    nombre: str = "base"

    @abc.abstractmethod
    def obtener(self) -> TasasVigentes:
        """Devuelve las tasas vigentes. Debe lanzar excepción si falla."""
