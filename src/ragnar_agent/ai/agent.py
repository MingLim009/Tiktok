"""Agente conversacional sobre la API de Claude.

Usa el bucle de tool-use manual (no el tool runner beta) para que el
entregable no dependa de una API en beta y para poder registrar cada
cotización y cada derivación en la base de datos.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, time

import anthropic

from .. import config
from ..config import get_settings
from ..logging_setup import get_logger
from ..rates import MotorDeTasas, get_motor
from . import tools
from .prompts import construir_sistema, contexto_del_turno

log = get_logger(__name__)

MAX_ITERACIONES = 6  # tope de vueltas del bucle de herramientas

_DIAS = {
    "lunes": 0, "martes": 1, "miercoles": 2, "miércoles": 2,
    "jueves": 3, "viernes": 4, "sabado": 5, "sábado": 5, "domingo": 6,
}


@dataclass
class Respuesta:
    texto: str
    derivar: bool = False
    motivo: str | None = None
    resumen: str | None = None
    telefono: str = ""
    horario: str = ""
    cotizaciones: list[dict] = field(default_factory=list)
    rechazada: bool = False


class AgenteIA:
    def __init__(self, motor: MotorDeTasas | None = None) -> None:
        s = get_settings()
        self._settings = s
        self._client = anthropic.Anthropic(api_key=s.require_api_key())
        self._motor = motor or get_motor()
        self._negocio = config.negocio()

        motivos = [
            m["id"]
            for m in (self._negocio.get("derivacion_humana", {}).get("motivos") or [])
        ] or ["peticion_explicita"]
        self._motivos = motivos
        self._tools = tools.definiciones(self._motor, motivos)
        self._sistema = construir_sistema(
            self._negocio, self._motor.operaciones_disponibles()
        )

    # -- horario ----------------------------------------------------------
    def _ahora(self) -> datetime:
        tz_nombre = self._negocio.get("horario", {}).get("zona_horaria")
        if tz_nombre:
            try:
                from zoneinfo import ZoneInfo

                return datetime.now(ZoneInfo(tz_nombre))
            except Exception:  # noqa: BLE001 - sin tzdata en Windows, por ejemplo
                log.debug("Zona horaria '%s' no disponible; uso hora local.", tz_nombre)
        return datetime.now()

    def esta_abierto(self, momento: datetime | None = None) -> bool:
        h = self._negocio.get("horario", {})
        ahora = momento or self._ahora()

        dias = {_DIAS[d.lower()] for d in h.get("dias", []) if d.lower() in _DIAS}
        if dias and ahora.weekday() not in dias:
            return False

        try:
            apertura = time.fromisoformat(str(h.get("apertura", "08:00")))
            cierre = time.fromisoformat(str(h.get("cierre", "17:00")))
        except ValueError:
            return True
        return apertura <= ahora.time() <= cierre

    # -- conversación -----------------------------------------------------
    def responder(
        self, mensaje: str, historial: list[dict[str, str]] | None = None
    ) -> Respuesta:
        """Genera la respuesta al último mensaje del cliente."""
        abierto = self.esta_abierto()
        contexto = contexto_del_turno(
            self._ahora().strftime("%Y-%m-%d %H:%M"),
            abierto,
            self._negocio.get("horario", {}).get("aviso_fuera_de_horario", ""),
        )

        mensajes: list[dict] = list(historial or [])
        mensajes.append({"role": "user", "content": f"{contexto}\n\n{mensaje}"})

        derivar = False
        motivo: str | None = None
        resumen: str | None = None
        telefono = ""
        horario = ""
        cotizaciones: list[dict] = []

        for vuelta in range(MAX_ITERACIONES):
            respuesta = self._client.messages.create(
                model=self._settings.anthropic_model,
                max_tokens=4096,
                system=[
                    {
                        "type": "text",
                        "text": self._sistema,
                        "cache_control": {"type": "ephemeral"},
                    }
                ],
                # Sin thinking explícito: en Claude Opus 5 el pensamiento está
                # activo por defecto, y desactivarlo hace que a veces las
                # llamadas a herramientas salgan como texto plano (y no se
                # ejecuten). `effort: low` mantiene el costo y la latencia bajos.
                output_config={"effort": "low"},
                tools=self._tools,
                messages=mensajes,
            )

            if respuesta.stop_reason == "refusal":
                log.warning("La API rechazó la solicitud por políticas de seguridad.")
                return Respuesta(
                    texto=self._negocio["derivacion_humana"]["mensaje_al_cliente"],
                    derivar=True,
                    motivo="peticion_explicita",
                    resumen="La IA no pudo responder este mensaje.",
                    rechazada=True,
                )

            if respuesta.stop_reason != "tool_use":
                return Respuesta(
                    texto=_texto(respuesta),
                    derivar=derivar,
                    motivo=motivo,
                    resumen=resumen,
                    telefono=telefono,
                    horario=horario,
                    cotizaciones=cotizaciones,
                )

            mensajes.append({"role": "assistant", "content": respuesta.content})

            resultados = []
            for bloque in respuesta.content:
                if bloque.type != "tool_use":
                    continue
                contenido, es_error, meta = tools.ejecutar(
                    bloque.name, dict(bloque.input), self._motor
                )
                if meta:
                    if meta.get("derivar"):
                        derivar = True
                        motivo = meta.get("motivo")
                        resumen = meta.get("resumen")
                        telefono = meta.get("telefono", "")
                        horario = meta.get("horario", "")
                    if meta.get("cotizacion"):
                        cotizaciones.append(meta["cotizacion"])

                resultado = {
                    "type": "tool_result",
                    "tool_use_id": bloque.id,
                    "content": contenido,
                }
                if es_error:
                    resultado["is_error"] = True
                resultados.append(resultado)

            mensajes.append({"role": "user", "content": resultados})
            log.debug("Vuelta %d del bucle de herramientas", vuelta + 1)

        log.warning("Se alcanzó el máximo de vueltas de herramientas.")
        return Respuesta(
            texto=(
                "Disculpa, se me complicó procesar eso. ¿Me lo repites de otra "
                "forma? O si prefieres, le paso tu consulta a un asesor 🙌"
            ),
            derivar=derivar,
            motivo=motivo,
            resumen=resumen,
            cotizaciones=cotizaciones,
        )


def _texto(respuesta) -> str:
    partes = [b.text for b in respuesta.content if b.type == "text"]
    return "\n".join(p.strip() for p in partes if p.strip()).strip()
