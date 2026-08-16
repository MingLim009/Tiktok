"""Tasas de respaldo escritas a mano en config/tasas.yaml.

Se usan sólo si la hoja no responde. Cada valor se convierte en una tabla de
un único tramo sin tope, para que el motor pueda cotizar igual — con una tasa
conservadora — en vez de quedarse mudo delante de un cliente.
"""

from __future__ import annotations

from .base import ProveedorDeTasas, TasasVigentes
from .tramos import TablaTramos, Tramo


class ManualProvider(ProveedorDeTasas):
    nombre = "manual"

    def __init__(self, valores: dict) -> None:
        self._valores = {str(k): float(v) for k, v in (valores or {}).items()}
        if not self._valores:
            raise ValueError(
                "La sección 'manual' de config/tasas.yaml está vacía. "
                "Agrega al menos BOB/PEN y PEN/BOB como respaldo."
            )

    def obtener(self) -> TasasVigentes:
        tablas = {
            nombre: TablaTramos(
                nombre=nombre,
                unidad="",
                tramos=[Tramo(desde=0.0, hasta=None, tasa=tasa)],
            )
            for nombre, tasa in self._valores.items()
        }
        return TasasVigentes(
            valores=dict(self._valores),
            fecha=None,
            fuente=self.nombre,
            tablas=tablas,
        )
