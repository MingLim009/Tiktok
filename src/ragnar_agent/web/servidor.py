"""Servidor del chat de prueba.

Sirve una página donde el cliente conversa con el bot desde su navegador,
sin instalar nada. NO toca TikTok: es sólo para revisar las respuestas.

Va protegido con contraseña porque queda expuesto a internet y cada mensaje
consume saldo de la cuenta de Claude del cliente. Sin clave, cualquiera que
encuentre el enlace le gasta el saldo.
"""

from __future__ import annotations

import json
import secrets
import threading
from base64 import b64decode
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from ..logging_setup import get_logger

log = get_logger(__name__)

PAGINA = Path(__file__).parent / "chat.html"
MAX_MENSAJE = 2000
MAX_HISTORIAL = 16


class _Estado:
    """Compartido entre peticiones. Una sola conversación: la revisa una persona."""

    def __init__(self, agente, usuario: str, clave: str) -> None:
        self.agente = agente
        self.usuario = usuario
        self.clave = clave
        self.historial: list[dict[str, str]] = []
        self.lock = threading.Lock()
        self.mensajes = 0


class _Handler(BaseHTTPRequestHandler):
    estado: _Estado = None  # se asigna al arrancar
    server_version = "RagnarChat"

    # -- utilidades -------------------------------------------------------
    def log_message(self, formato, *args):  # noqa: A003 - silencia el log ruidoso
        pass

    def _json(self, datos: dict, codigo: int = 200) -> None:
        cuerpo = json.dumps(datos, ensure_ascii=False).encode("utf-8")
        self.send_response(codigo)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(cuerpo)))
        self.end_headers()
        self.wfile.write(cuerpo)

    def _autorizado(self) -> bool:
        cabecera = self.headers.get("Authorization", "")
        if not cabecera.startswith("Basic "):
            return False
        try:
            usuario, _, clave = b64decode(cabecera[6:]).decode("utf-8").partition(":")
        except Exception:  # noqa: BLE001
            return False
        # compare_digest evita filtrar la clave por el tiempo de respuesta.
        return (
            secrets.compare_digest(usuario, self.estado.usuario)
            and secrets.compare_digest(clave, self.estado.clave)
        )

    def _pedir_clave(self) -> None:
        self.send_response(401)
        self.send_header("WWW-Authenticate", 'Basic realm="Ragnar Capital"')
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(
            "<h2>Acceso restringido</h2><p>Pide el usuario y la clave a Kelvin.</p>"
            .encode("utf-8")
        )

    # -- rutas ------------------------------------------------------------
    def do_GET(self) -> None:  # noqa: N802 - lo exige BaseHTTPRequestHandler
        if not self._autorizado():
            return self._pedir_clave()

        ruta = self.path.split("?")[0].rstrip("/") or "/"

        if ruta in ("/", "/chat"):
            cuerpo = PAGINA.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(cuerpo)))
            self.end_headers()
            return self.wfile.write(cuerpo)

        if ruta == "/api/estado":
            try:
                tasas = self.estado.agente._motor.tasas_crudas()  # noqa: SLF001
                return self._json({
                    "tasas": True, "fecha": tasas.fecha, "fuente": tasas.fuente,
                })
            except Exception as exc:  # noqa: BLE001
                return self._json({"tasas": False, "error": str(exc)})

        self._json({"error": "no encontrado"}, 404)

    def do_POST(self) -> None:  # noqa: N802
        if not self._autorizado():
            return self._pedir_clave()

        if self.path.split("?")[0].rstrip("/") != "/api/mensaje":
            return self._json({"error": "no encontrado"}, 404)

        try:
            largo = int(self.headers.get("Content-Length", 0))
            datos = json.loads(self.rfile.read(largo) or b"{}")
            mensaje = str(datos.get("mensaje", "")).strip()[:MAX_MENSAJE]
        except Exception:  # noqa: BLE001
            return self._json({"error": "No se entendió el mensaje."}, 400)

        if not mensaje:
            return self._json({"error": "Escribe algo primero."}, 400)

        est = self.estado
        # Un solo mensaje a la vez: comparten historial y es una sola persona.
        with est.lock:
            try:
                r = est.agente.responder(mensaje, est.historial)
            except Exception as exc:  # noqa: BLE001
                log.exception("Error respondiendo")
                return self._json({
                    "error": f"No se pudo responder: {exc}"
                }, 500)

            est.historial.append({"role": "user", "content": mensaje})
            est.historial.append({"role": "assistant", "content": r.texto})
            est.historial = est.historial[-MAX_HISTORIAL:]
            est.mensajes += 1

        log.info("[%d] %s → %s", est.mensajes, mensaje[:60], r.texto[:70])

        self._json({
            "texto": r.texto,
            "derivar": r.derivar,
            "motivo": r.motivo,
            "telefono": r.telefono,
            "cotizaciones": r.cotizaciones,
        })


def lanzar(agente, puerto: int, usuario: str, clave: str):
    """Arranca el servidor. Devuelve la instancia para poder cerrarla."""
    _Handler.estado = _Estado(agente, usuario, clave)
    servidor = ThreadingHTTPServer(("0.0.0.0", puerto), _Handler)
    hilo = threading.Thread(target=servidor.serve_forever, daemon=True)
    hilo.start()
    return servidor
