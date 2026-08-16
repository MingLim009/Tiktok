"""Controles anti-bloqueo para el envío de mensajes directos.

Nada de esto oculta que hay automatización: son límites de volumen y ritmo
para que la cuenta se comporte como una persona atendiendo clientes y no
como un emisor masivo. El riesgo de restricción NUNCA llega a cero; TikTok
no autoriza el envío automatizado de DMs. Ver docs/SEGURIDAD.md.
"""

from __future__ import annotations

import enum
import random
import time
from dataclasses import dataclass
from datetime import datetime, timedelta

from ..logging_setup import get_logger
from ..store import Store

log = get_logger(__name__)


class MotivoBloqueo(enum.Enum):
    OK = "ok"
    LIMITE_HORA = "limite_hora"
    LIMITE_DIA = "limite_dia"
    YA_CONTACTADO = "ya_contactado"


@dataclass
class Decision:
    permitido: bool
    motivo: MotivoBloqueo
    detalle: str = ""


class Limitador:
    def __init__(self, store: Store, limites: dict) -> None:
        self._store = store
        self._por_hora = int(limites.get("dm_por_hora", 25))
        self._por_dia = int(limites.get("dm_por_dia", 150))
        espera = limites.get("espera_entre_dm", [35, 95])
        self._espera_min = float(espera[0])
        self._espera_max = float(espera[1])
        self._no_repetir_horas = int(limites.get("no_repetir_horas", 72))
        self._ultimo_envio: float = 0.0

    def evaluar(self, usuario: str) -> Decision:
        """¿Se le puede escribir a este usuario ahora mismo?"""
        if self._no_repetir_horas and self._store.escrito_recientemente(
            usuario, self._no_repetir_horas
        ):
            return Decision(
                False,
                MotivoBloqueo.YA_CONTACTADO,
                f"ya se le escribió en las últimas {self._no_repetir_horas} h",
            )

        ahora = datetime.now()
        en_hora = self._store.dms_desde(ahora - timedelta(hours=1))
        if en_hora >= self._por_hora:
            return Decision(
                False,
                MotivoBloqueo.LIMITE_HORA,
                f"{en_hora}/{self._por_hora} DMs en la última hora",
            )

        en_dia = self._store.dms_desde(ahora - timedelta(days=1))
        if en_dia >= self._por_dia:
            return Decision(
                False,
                MotivoBloqueo.LIMITE_DIA,
                f"{en_dia}/{self._por_dia} DMs en las últimas 24 h",
            )

        return Decision(True, MotivoBloqueo.OK)

    def esperar_turno(self) -> None:
        """Bloquea hasta que haya pasado un intervalo aleatorio desde el último envío.

        La aleatoriedad es intencional: un envío cada N segundos exactos es
        justamente el patrón que se detecta como automatización.
        """
        objetivo = random.uniform(self._espera_min, self._espera_max)
        transcurrido = time.monotonic() - self._ultimo_envio
        restante = objetivo - transcurrido
        if restante > 0 and self._ultimo_envio > 0:
            log.debug("Esperando %.1f s antes del próximo envío", restante)
            time.sleep(restante)

    def registrar_envio(self, usuario: str, origen: str, regla_id: str | None = None):
        self._ultimo_envio = time.monotonic()
        self._store.registrar_dm(usuario, origen, regla_id)

    def resumen(self) -> str:
        ahora = datetime.now()
        return (
            f"{self._store.dms_desde(ahora - timedelta(hours=1))}/{self._por_hora} por hora · "
            f"{self._store.dms_desde(ahora - timedelta(days=1))}/{self._por_dia} por día"
        )
