"""Lectura de tasas desde Odoo por XML-RPC.

Pendiente de que Ragnar Capital entregue los accesos (URL, base, usuario y
API key). La estructura ya está lista: cuando lleguen los datos sólo hay que
completar `odoo.campos` en config/tasas.yaml con el mapeo

    "RC. BOB/PEN": {"modelo": "res.currency.rate", "dominio": [...], "campo": "rate"}

y cambiar `fuente: odoo`. No hay que tocar el resto del sistema: el motor de
cotización consume la misma interfaz que el proveedor de Google Sheet.
"""

from __future__ import annotations

import xmlrpc.client
from typing import Any

from ..logging_setup import get_logger
from .base import ProveedorDeTasas, TasasVigentes

log = get_logger(__name__)


class OdooProvider(ProveedorDeTasas):
    nombre = "odoo"

    def __init__(self, url: str, db: str, username: str, api_key: str, campos: dict):
        if not all([url, db, username, api_key]):
            raise ValueError(
                "Faltan credenciales de Odoo. Completa ODOO_URL, ODOO_DB, "
                "ODOO_USERNAME y ODOO_API_KEY en el archivo .env"
            )
        self._url = url.rstrip("/")
        self._db = db
        self._username = username
        self._api_key = api_key
        self._campos = campos or {}
        self._uid: int | None = None

    def _conectar(self) -> tuple[int, Any]:
        if self._uid is None:
            common = xmlrpc.client.ServerProxy(f"{self._url}/xmlrpc/2/common")
            uid = common.authenticate(self._db, self._username, self._api_key, {})
            if not uid:
                raise RuntimeError(
                    "Odoo rechazó las credenciales (usuario o API key incorrectos)."
                )
            self._uid = uid
        models = xmlrpc.client.ServerProxy(f"{self._url}/xmlrpc/2/object")
        return self._uid, models

    def obtener(self) -> TasasVigentes:
        if not self._campos:
            raise RuntimeError(
                "config/tasas.yaml -> odoo.campos está vacío: todavía no sabemos "
                "en qué modelo/campo de Odoo viven las tasas de Ragnar Capital."
            )

        uid, models = self._conectar()
        valores: dict[str, float] = {}

        for columna, spec in self._campos.items():
            modelo = spec["modelo"]
            dominio = spec.get("dominio", [])
            campo = spec.get("campo", "rate")
            registros = models.execute_kw(
                self._db,
                uid,
                self._api_key,
                modelo,
                "search_read",
                [dominio],
                {"fields": [campo], "limit": 1, "order": "id desc"},
            )
            if registros:
                valores[columna] = float(registros[0][campo])
            else:
                log.warning("Odoo no devolvió registros para la columna %s", columna)

        if not valores:
            raise RuntimeError("Odoo no devolvió ninguna tasa.")
        return TasasVigentes(valores=valores, fuente=self.nombre)
