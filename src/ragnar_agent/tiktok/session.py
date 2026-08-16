"""Sesión de navegador para TikTok.

TikTok no tiene API oficial de mensajes directos, así que se automatiza el
sitio web con un navegador real (Playwright).

Sobre la contraseña: NO se guarda en ningún lado ni se escribe por código.
El login se hace UNA sola vez a mano, en una ventana de navegador que abre
este programa (`python -m ragnar_agent.cli.login`). A partir de ahí queda
guardada la sesión (cookies) en la carpeta del perfil, igual que en tu
navegador de siempre. Esa carpeta vale tanto como la contraseña: trátala así.
"""

from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from typing import Any

from ..config import get_settings
from ..logging_setup import get_logger

log = get_logger(__name__)

URL_MENSAJES = "https://www.tiktok.com/messages"
URL_LOGIN = "https://www.tiktok.com/login"

# Un user-agent de escritorio real: TikTok le sirve una interfaz distinta
# (y más limitada) a los clientes que no reconoce.
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)


class SesionNoIniciada(RuntimeError):
    """No hay sesión guardada, o TikTok la cerró."""


class SesionEnUso(RuntimeError):
    """Otro proceso ya está usando la sesión del navegador.

    Dos procesos sobre el mismo perfil de Chromium corrompen las cookies y
    terminan cerrando la sesión de TikTok. Pasa si se corre `run_dm` y
    `run_live --enviar` al mismo tiempo.
    """


class SesionTikTok:
    """Envuelve un contexto persistente de Playwright.

    Uso:
        with SesionTikTok() as s:
            page = s.abrir_mensajes()
    """

    def __init__(self, headless: bool | None = None) -> None:
        s = get_settings()
        self._perfil: Path = s.tiktok_profile_dir
        self._headless = True if headless is None else headless
        self._pw: Any = None
        self._context: Any = None
        self._tengo_candado = False

    # -- ciclo de vida ----------------------------------------------------
    def __enter__(self) -> SesionTikTok:
        self.iniciar()
        return self

    def __exit__(self, *exc: object) -> None:
        self.cerrar()

    # -- candado ----------------------------------------------------------
    @property
    def _candado(self) -> Path:
        return self._perfil.parent / "sesion.lock"

    def _tomar_candado(self) -> None:
        candado = self._candado
        candado.parent.mkdir(parents=True, exist_ok=True)
        try:
            # 'x' falla si el archivo ya existe: es la operación atómica que
            # evita que dos procesos se pisen.
            with candado.open("x", encoding="utf-8") as fh:
                fh.write(f"pid={os.getpid()}\ninicio={datetime.now().isoformat()}\n")
        except FileExistsError:
            detalle = ""
            try:
                detalle = candado.read_text(encoding="utf-8").strip().replace("\n", " · ")
            except OSError:
                pass
            raise SesionEnUso(
                "Ya hay otro proceso usando la sesión de TikTok "
                f"({detalle or 'sin datos'}).\n\n"
                "No se puede correr el bot de bandeja y el de Live al mismo\n"
                "tiempo: comparten el mismo navegador y se corrompe la sesión.\n\n"
                "  · Si el otro proceso sigue abierto, ciérralo con Ctrl+C.\n"
                "  · Si se cerró mal y quedó trabado, borra este archivo:\n"
                f"      {candado}"
            ) from None
        self._tengo_candado = True

    def _soltar_candado(self) -> None:
        if getattr(self, "_tengo_candado", False):
            self._candado.unlink(missing_ok=True)
            self._tengo_candado = False

    def iniciar(self) -> None:
        try:
            from playwright.sync_api import sync_playwright
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError(
                "Falta Playwright. Instálalo con:\n"
                "  pip install playwright\n"
                "  playwright install chromium"
            ) from exc

        self._tomar_candado()
        try:
            self._perfil.mkdir(parents=True, exist_ok=True)
            self._pw = sync_playwright().start()
            self._context = self._pw.chromium.launch_persistent_context(
                user_data_dir=str(self._perfil),
                headless=self._headless,
                user_agent=USER_AGENT,
                viewport={"width": 1360, "height": 900},
                locale="es-PE",
                args=["--disable-blink-features=AutomationControlled"],
            )
        except Exception:
            # Si el navegador no arrancó, el candado no debe quedar trabado.
            if self._pw is not None:
                self._pw.stop()
                self._pw = None
            self._soltar_candado()
            raise
        log.debug("Contexto de navegador iniciado en %s", self._perfil)

    def cerrar(self) -> None:
        try:
            if self._context is not None:
                self._context.close()
        finally:
            if self._pw is not None:
                self._pw.stop()
            self._context = None
            self._pw = None
            self._soltar_candado()

    # -- navegación -------------------------------------------------------
    @property
    def context(self) -> Any:
        if self._context is None:
            raise RuntimeError("La sesión no está iniciada (usa 'with SesionTikTok()').")
        return self._context

    def nueva_pagina(self) -> Any:
        paginas = self.context.pages
        return paginas[0] if paginas else self.context.new_page()

    def abrir_mensajes(self) -> Any:
        """Abre la bandeja y verifica que la sesión siga viva."""
        page = self.nueva_pagina()
        page.goto(URL_MENSAJES, wait_until="domcontentloaded", timeout=60_000)
        page.wait_for_timeout(3_000)

        if not self.sesion_valida(page):
            raise SesionNoIniciada(
                "TikTok no reconoce la sesión guardada.\n"
                "Vuelve a iniciar sesión con:  python -m ragnar_agent.cli.login"
            )
        return page

    def sesion_valida(self, page: Any) -> bool:
        url = page.url or ""
        if "/login" in url or "/signup" in url:
            return False
        # Si aparece el botón de iniciar sesión, no hay sesión.
        try:
            botones = page.get_by_text("Iniciar sesión", exact=False)
            if botones.count() > 0 and botones.first.is_visible():
                return False
        except Exception:  # noqa: BLE001 - la UI cambia; ante la duda, seguimos
            pass
        return True

    def guardar_captura(self, page: Any, nombre: str) -> Path:
        """Captura de pantalla para diagnosticar cuándo cambia la interfaz."""
        destino = self._perfil.parent / f"{nombre}.png"
        page.screenshot(path=str(destino), full_page=False)
        log.info("Captura guardada en %s", destino)
        return destino
