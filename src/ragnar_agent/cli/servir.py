"""Levanta el chat de prueba para que el cliente lo abra desde su navegador.

    python -m ragnar_agent.cli.servir

Genera una clave, arranca el servidor y explica cómo exponerlo a internet.
No toca TikTok: es sólo para revisar las respuestas del bot.
"""

from __future__ import annotations

import argparse
import secrets
import socket
import sys
import time

from ..config import get_settings
from ..logging_setup import setup
from ..web import lanzar

USUARIO = "ragnar"


def _ip_local() -> str:
    """IP de esta máquina en la red local, para probar desde el celular."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:  # noqa: BLE001
        return "127.0.0.1"


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Chat de prueba del bot")
    p.add_argument("--puerto", type=int, default=8080)
    p.add_argument("--clave", default=None,
                   help="Clave de acceso (si no, se genera una)")
    args = p.parse_args(argv)

    setup(get_settings().log_level)

    from . import crear_agente

    agente = crear_agente()
    if agente is None:
        return 2

    clave = args.clave or secrets.token_urlsafe(9)
    servidor = lanzar(agente, args.puerto, USUARIO, clave)
    ip = _ip_local()

    print()
    print("=" * 70)
    print("  CHAT DE PRUEBA — funcionando")
    print("=" * 70)
    print()
    print("  Para probarlo tú, aquí mismo:")
    print(f"      http://localhost:{args.puerto}")
    print()
    print("  Desde otro equipo de tu misma red (tu celular, por ejemplo):")
    print(f"      http://{ip}:{args.puerto}")
    print()
    print("  Usuario:  " + USUARIO)
    print("  Clave:    " + clave)
    print()
    print("-" * 70)
    print("  PARA QUE EL CLIENTE ENTRE DESDE OTRO PAÍS")
    print("-" * 70)
    print()
    print("  Necesitas exponerlo a internet. En otra ventana, corre UNA")
    print("  de estas (la que tengas instalada):")
    print()
    print(f"      cloudflared tunnel --url http://localhost:{args.puerto}")
    print(f"      ngrok http {args.puerto}")
    print()
    print("  Cualquiera te va a dar un enlace público. Ese es el que le")
    print("  mandas, junto con el usuario y la clave de arriba.")
    print()
    print("-" * 70)
    print("  Esto NO está conectado a TikTok. Sólo sirve para revisar las")
    print("  respuestas. Cada mensaje consume saldo de la cuenta de Claude.")
    print()
    print("  Para detenerlo: Ctrl + C")
    print("=" * 70)
    print()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n  Cerrando…")
        servidor.shutdown()
        print("  Servidor detenido.\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
