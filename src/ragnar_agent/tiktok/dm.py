"""Lectura y respuesta de la bandeja de mensajes directos de TikTok.

⚠️  Los selectores de esta clase dependen del HTML de tiktok.com, que TikTok
    cambia sin avisar. Por eso están TODOS juntos aquí arriba y cada uno tiene
    varias alternativas: cuando algo deje de funcionar, se ajusta este bloque
    y nada más. `python -m ragnar_agent.cli.run_dm --diagnostico` guarda una
    captura y el HTML de la bandeja para poder corregirlos rápido.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from ..logging_setup import get_logger

log = get_logger(__name__)

# --------------------------------------------------------------------------
#  SELECTORES  (ajustar aquí si TikTok cambia la interfaz)
# --------------------------------------------------------------------------
SEL_LISTA_CONVERSACIONES = [
    "div[data-e2e='chat-list-item']",
    "div[class*='DivChatListItem']",
    "div[class*='chat-list'] > div[role='button']",
]
SEL_NOMBRE_EN_ITEM = [
    "[data-e2e='chat-list-nickname']",
    "p[class*='PNickName']",
    "span[class*='nickname']",
]
SEL_PREVIEW_EN_ITEM = [
    "[data-e2e='chat-list-msg']",
    "p[class*='PInfoExtractTime']",
    "div[class*='last-message']",
]
SEL_BURBUJAS = [
    "div[data-e2e='chat-item']",
    "div[class*='DivChatItemWrapper']",
    "div[class*='message-item']",
]
SEL_CAJA_TEXTO = [
    "div[data-e2e='message-input-area'] div[contenteditable='true']",
    "div[contenteditable='true'][role='textbox']",
    "div[contenteditable='plaintext-only']",
    "textarea[placeholder*='ensaje']",
]
SEL_BOTON_ENVIAR = [
    "[data-e2e='message-send']",
    "svg[data-e2e='message-send']",
    "button[type='submit']",
]
# Marca de "no leído" en la lista de conversaciones
SEL_NO_LEIDO = [
    "[data-e2e='chat-list-unread']",
    "span[class*='Badge']",
    "div[class*='unread']",
]


@dataclass
class Conversacion:
    indice: int
    usuario: str
    preview: str
    no_leido: bool

    @property
    def thread_id(self) -> str:
        return f"tiktok:{self.usuario}"


@dataclass
class Mensaje:
    texto: str
    entrante: bool


def _buscar(raiz: Any, selectores: list[str]) -> Any | None:
    """Devuelve el primer locator que encuentre algo, o None."""
    for sel in selectores:
        try:
            loc = raiz.locator(sel)
            if loc.count() > 0:
                return loc
        except Exception:  # noqa: BLE001 - selector inválido para esta vista
            continue
    return None


def _texto_de(raiz: Any, selectores: list[str], por_defecto: str = "") -> str:
    loc = _buscar(raiz, selectores)
    if loc is None:
        return por_defecto
    try:
        return (loc.first.inner_text() or por_defecto).strip()
    except Exception:  # noqa: BLE001
        return por_defecto


class Bandeja:
    """Opera sobre la página de mensajes ya abierta y con sesión válida."""

    def __init__(self, page: Any) -> None:
        self._page = page

    # -- lectura ----------------------------------------------------------
    def conversaciones(self, limite: int = 20) -> list[Conversacion]:
        lista = _buscar(self._page, SEL_LISTA_CONVERSACIONES)
        if lista is None:
            log.warning(
                "No se encontró la lista de conversaciones. La interfaz de TikTok "
                "probablemente cambió: corre con --diagnostico y ajusta "
                "SEL_LISTA_CONVERSACIONES en src/ragnar_agent/tiktok/dm.py"
            )
            return []

        total = min(lista.count(), limite)
        resultado: list[Conversacion] = []
        for i in range(total):
            item = lista.nth(i)
            try:
                usuario = _texto_de(item, SEL_NOMBRE_EN_ITEM, f"usuario_{i}")
                preview = _texto_de(item, SEL_PREVIEW_EN_ITEM)
                no_leido = _buscar(item, SEL_NO_LEIDO) is not None
            except Exception:  # noqa: BLE001
                continue
            resultado.append(
                Conversacion(
                    indice=i,
                    usuario=_limpiar_usuario(usuario),
                    preview=preview,
                    no_leido=no_leido,
                )
            )
        return resultado

    def abrir(self, conversacion: Conversacion) -> bool:
        lista = _buscar(self._page, SEL_LISTA_CONVERSACIONES)
        if lista is None or lista.count() <= conversacion.indice:
            return False
        try:
            lista.nth(conversacion.indice).click(timeout=10_000)
            self._page.wait_for_timeout(2_000)
            return True
        except Exception as exc:  # noqa: BLE001
            log.warning("No se pudo abrir la conversación de %s: %s",
                        conversacion.usuario, exc)
            return False

    def mensajes(self, ultimos: int = 12) -> list[Mensaje]:
        """Lee las burbujas visibles del chat abierto.

        Distinguir quién escribió cada burbuja es lo más frágil de todo esto:
        TikTok no marca el autor de forma estable. Se usa la posición horizontal
        (los mensajes propios se alinean a la derecha), que es lo que se
        mantiene aunque cambien las clases CSS.
        """
        burbujas = _buscar(self._page, SEL_BURBUJAS)
        if burbujas is None:
            return []

        ancho = self._page.viewport_size["width"] if self._page.viewport_size else 1360
        total = burbujas.count()
        salida: list[Mensaje] = []

        for i in range(max(0, total - ultimos), total):
            b = burbujas.nth(i)
            try:
                texto = (b.inner_text() or "").strip()
                if not texto:
                    continue
                caja = b.bounding_box()
                # Centro de la burbuja a la derecha de la mitad => es nuestro.
                propio = bool(caja and (caja["x"] + caja["width"] / 2) > ancho * 0.55)
                salida.append(Mensaje(texto=texto, entrante=not propio))
            except Exception:  # noqa: BLE001
                continue
        return salida

    def ultimo_entrante(self) -> str | None:
        for m in reversed(self.mensajes()):
            if m.entrante:
                return m.texto
            # Si lo último es nuestro, ya respondimos: no hay nada que hacer.
            return None
        return None

    # -- escritura --------------------------------------------------------
    def enviar(self, texto: str) -> bool:
        caja = _buscar(self._page, SEL_CAJA_TEXTO)
        if caja is None:
            log.error(
                "No se encontró la caja de texto. Ajusta SEL_CAJA_TEXTO en "
                "src/ragnar_agent/tiktok/dm.py"
            )
            return False

        try:
            caja.first.click(timeout=10_000)
            self._page.wait_for_timeout(400)
            # Escribir con retardo por carácter: un pegado instantáneo de 200
            # caracteres es justo el patrón que TikTok marca como automatizado.
            caja.first.type(texto, delay=28)
            self._page.wait_for_timeout(600)

            boton = _buscar(self._page, SEL_BOTON_ENVIAR)
            if boton is not None and boton.first.is_visible():
                boton.first.click(timeout=8_000)
            else:
                self._page.keyboard.press("Enter")

            self._page.wait_for_timeout(1_500)
            return True
        except Exception as exc:  # noqa: BLE001
            log.error("Falló el envío del mensaje: %s", exc)
            return False

    # -- diagnóstico ------------------------------------------------------
    def volcar_diagnostico(self, destino_html: str) -> None:
        try:
            html = self._page.content()
            with open(destino_html, "w", encoding="utf-8") as fh:
                fh.write(html)
            log.info("HTML de la bandeja guardado en %s", destino_html)
        except Exception as exc:  # noqa: BLE001
            log.warning("No se pudo volcar el HTML: %s", exc)


def _limpiar_usuario(valor: str) -> str:
    valor = re.sub(r"\s+", " ", valor or "").strip()
    return valor.lstrip("@") or "desconocido"


# --------------------------------------------------------------------------
#  Abrir un chat con un usuario concreto (lo usa el bot de Live)
# --------------------------------------------------------------------------
SEL_BOTON_MENSAJE_PERFIL = [
    "[data-e2e='message-button']",
    "button:has-text('Mensaje')",
    "button:has-text('Message')",
    "div[role='button']:has-text('Mensaje')",
]


def abrir_chat_con(page: Any, usuario: str, timeout_ms: int = 30_000) -> Bandeja | None:
    """Entra al perfil de @usuario y abre el chat con él.

    Devuelve una Bandeja lista para `enviar()`, o None si no se pudo.
    Falla (devolviendo None) cuando el usuario tiene los mensajes cerrados a
    desconocidos, que es un caso normal y no un error del sistema.
    """
    usuario = (usuario or "").lstrip("@")
    if not usuario:
        return None

    try:
        page.goto(
            f"https://www.tiktok.com/@{usuario}",
            wait_until="domcontentloaded",
            timeout=timeout_ms,
        )
        page.wait_for_timeout(2_500)
    except Exception as exc:  # noqa: BLE001
        log.warning("No se pudo abrir el perfil de @%s: %s", usuario, exc)
        return None

    boton = _buscar(page, SEL_BOTON_MENSAJE_PERFIL)
    if boton is None:
        log.info(
            "@%s no muestra el botón de mensaje (perfil privado, mensajes "
            "cerrados a desconocidos, o cambió la interfaz). Se omite.",
            usuario,
        )
        return None

    try:
        boton.first.click(timeout=10_000)
        page.wait_for_timeout(3_000)
    except Exception as exc:  # noqa: BLE001
        log.warning("No se pudo abrir el chat con @%s: %s", usuario, exc)
        return None

    bandeja = Bandeja(page)
    if _buscar(page, SEL_CAJA_TEXTO) is None:
        log.info("Se abrió el perfil de @%s pero no apareció la caja de texto.", usuario)
        return None
    return bandeja
