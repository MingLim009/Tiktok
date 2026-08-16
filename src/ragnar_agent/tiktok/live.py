"""Monitoreo de comentarios de TikTok Live y detección de palabras clave.

Usa la librería TikTokLive (conector no oficial). No requiere iniciar sesión:
lee el mismo flujo de comentarios que ve cualquier espectador. El envío del DM
sí requiere la sesión del navegador (ver session.py / dm.py).
"""

from __future__ import annotations

import random
import re
import unicodedata
from dataclasses import dataclass
from typing import Callable

from ..logging_setup import get_logger

log = get_logger(__name__)


@dataclass
class Regla:
    id: str
    palabras: list[str]
    exacta: bool
    plantillas: list[str]

    def mensaje_para(self, nombre: str) -> str:
        plantilla = random.choice(self.plantillas)
        return plantilla.replace("{nombre}", nombre or "")


@dataclass
class Coincidencia:
    usuario: str
    nombre: str
    comentario: str
    regla: Regla


def identificar(user: object) -> tuple[str, str]:
    """Saca (handle, nombre) del autor de un comentario.

    El handle es lo único que sirve para abrirle el chat: la URL del perfil
    es tiktok.com/@handle. El nombre sólo se usa para saludar.

    Ojo con los nombres de los campos: en TikTokLive 6.x el handle está en
    `display_id`, NO en `unique_id` (ese campo no existe y devolvía vacío en
    silencio, con lo cual nunca se enviaba ningún DM). Se prueban varios por
    si cambian entre versiones.
    """
    handle = ""
    for campo in ("display_id", "unique_id", "uniqueId"):
        valor = getattr(user, campo, "") or ""
        if valor:
            handle = str(valor).lstrip("@")
            break

    nombre = str(getattr(user, "nickname", "") or "") or handle
    return handle, nombre


def normalizar(texto: str) -> str:
    """minúsculas, sin tildes y sin signos — para comparar comentarios.

    Así 'Yo!', 'yo', 'YO.' y 'yó' cuentan todos como la palabra clave 'yo'.
    """
    texto = (texto or "").strip().lower()
    texto = unicodedata.normalize("NFD", texto)
    texto = "".join(c for c in texto if unicodedata.category(c) != "Mn")
    return re.sub(r"[^\w\s]", "", texto).strip()


def cargar_reglas(cfg: dict) -> list[Regla]:
    reglas = []
    for r in cfg.get("reglas", []) or []:
        if not r.get("activa", True):
            continue
        plantillas = r.get("plantillas") or []
        if not plantillas:
            log.warning("La regla '%s' no tiene plantillas; se omite.", r.get("id"))
            continue
        reglas.append(
            Regla(
                id=str(r.get("id", "sin_id")),
                palabras=[normalizar(p) for p in r.get("palabras_clave", [])],
                exacta=bool(r.get("exacta", True)),
                plantillas=plantillas,
            )
        )
    return reglas


def evaluar(comentario: str, reglas: list[Regla]) -> Regla | None:
    """Primera regla que coincida, o None."""
    texto = normalizar(comentario)
    if not texto:
        return None

    palabras_del_texto = set(texto.split())
    for regla in reglas:
        for clave in regla.palabras:
            if not clave:
                continue
            if regla.exacta:
                # Coincide si el comentario ES la palabra clave, o si es una
                # de sus palabras cuando el comentario es muy corto ("yo!!" -> "yo").
                if texto == clave or (len(palabras_del_texto) <= 2 and clave in palabras_del_texto):
                    return regla
            elif clave in texto:
                return regla
    return None


class MonitorLive:
    """Escucha los comentarios de un live y avisa por callback."""

    def __init__(self, cuenta: str, reglas: list[Regla],
                 al_detectar: Callable[[Coincidencia], None]) -> None:
        self._cuenta = cuenta.lstrip("@")
        self._reglas = reglas
        self._callback = al_detectar

    def ejecutar(self) -> None:
        try:
            from TikTokLive import TikTokLiveClient
            from TikTokLive.events import CommentEvent, ConnectEvent, DisconnectEvent
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError(
                "Falta la librería TikTokLive. Instálala con:\n"
                "  pip install TikTokLive"
            ) from exc

        cliente = TikTokLiveClient(unique_id=f"@{self._cuenta}")

        @cliente.on(ConnectEvent)
        async def _conectado(evento):  # noqa: ANN001, ARG001
            log.info("Conectado al live de @%s. Escuchando comentarios…", self._cuenta)

        @cliente.on(DisconnectEvent)
        async def _desconectado(evento):  # noqa: ANN001, ARG001
            log.warning("Se cerró la conexión con el live.")

        @cliente.on(CommentEvent)
        async def _comentario(evento):  # noqa: ANN001
            texto = getattr(evento, "comment", "") or ""
            usuario, nombre = identificar(getattr(evento, "user", None))

            regla = evaluar(texto, self._reglas)
            if regla is None:
                return

            if not usuario:
                # Sin handle no hay a quién escribirle. Si esto aparece seguido,
                # cambió el nombre del campo en la librería: revisar identificar().
                log.warning(
                    "Keyword '%s' detectada en %r pero el comentario no trae "
                    "handle del usuario; no se puede enviar el DM.",
                    regla.id, texto[:60],
                )
                return

            log.info("Keyword '%s' detectada — @%s: %r", regla.id, usuario, texto)
            try:
                self._callback(
                    Coincidencia(
                        usuario=usuario, nombre=nombre, comentario=texto, regla=regla
                    )
                )
            except Exception:  # noqa: BLE001 - un fallo no debe cortar el live
                log.exception("Error procesando la coincidencia de @%s", usuario)

        log.info(
            "Esperando a que @%s inicie transmisión "
            "(si ya está en vivo, conecta enseguida)…",
            self._cuenta,
        )
        cliente.run()
