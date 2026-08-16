"""Inicio de sesión guiado en TikTok (se hace UNA sola vez).

    python -m ragnar_agent.cli.login

Abre una ventana de Chromium en la página de TikTok. Inicias sesión a mano
—usuario, contraseña y el código de verificación que te llegue al correo— y el
programa guarda la sesión para que el bot no tenga que volver a pedirla.

La contraseña no pasa por el código, ni se guarda, ni queda en los logs.
"""

from __future__ import annotations

import sys
import time

from ..config import get_settings
from ..logging_setup import get_logger, setup
from ..tiktok.session import URL_LOGIN, SesionTikTok

log = get_logger(__name__)

ESPERA_MAXIMA_SEG = 600  # 10 minutos para completar el login


def main() -> int:
    s = get_settings()
    setup(s.log_level)

    print()
    print("=" * 68)
    print("  INICIO DE SESIÓN EN TIKTOK — Ragnar Capital")
    print("=" * 68)
    print()
    print("  Se va a abrir una ventana de navegador.")
    print("  1. Inicia sesión con tu cuenta de TikTok.")
    print("  2. Cuando pida el código de verificación, elige CORREO.")
    print("  3. Cuando ya veas tu bandeja de mensajes, vuelve aquí.")
    print()
    print(f"  La sesión se guardará en: {s.tiktok_profile_dir}")
    print("  ⚠️  Esa carpeta da acceso a la cuenta. No la compartas ni la subas")
    print("      a ningún repositorio.")
    print()
    input("  Presiona ENTER para abrir el navegador… ")

    with SesionTikTok(headless=False) as sesion:
        page = sesion.nueva_pagina()
        page.goto(URL_LOGIN, wait_until="domcontentloaded", timeout=60_000)

        print()
        print("  Navegador abierto. Inicia sesión ahí.")
        print("  Esperando… (hasta 10 minutos)")
        print()

        inicio = time.time()
        confirmado = False
        while time.time() - inicio < ESPERA_MAXIMA_SEG:
            page.wait_for_timeout(3_000)
            url = page.url or ""
            if "/login" not in url and "/signup" not in url:
                # Confirmar de verdad entrando a la bandeja.
                try:
                    page.goto(
                        "https://www.tiktok.com/messages",
                        wait_until="domcontentloaded",
                        timeout=45_000,
                    )
                    page.wait_for_timeout(4_000)
                    if sesion.sesion_valida(page):
                        confirmado = True
                        break
                except Exception:  # noqa: BLE001
                    pass

        if not confirmado:
            print()
            print("  ✗ No se detectó la sesión. Si alcanzaste a iniciar sesión,")
            print("    vuelve a correr este comando y espera a ver la bandeja.")
            return 1

        sesion.guardar_captura(page, "login_ok")
        print()
        print("  ✓ Sesión iniciada y guardada.")
        print()
        print("  Siguiente paso — probar el bot SIN enviar nada:")
        print("      python -m ragnar_agent.cli.run_dm")
        print()
        return 0


if __name__ == "__main__":
    sys.exit(main())
