"""Crea y abre el archivo de configuración (.env) con la clave de Claude.

    python -m ragnar_agent.cli.configurar

Pensado para alguien que no programa. Comprueba si la clave está PUESTA, no
si el archivo existe: si sólo se mirara la existencia, bastaría con que algo
saliera mal la primera vez para que no volviera a ofrecerse nunca más y la
persona quedara sin forma de avanzar.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from ..config import ROOT

PLANTILLA = ROOT / ".env.example"
DESTINO = ROOT / ".env"
MARCADOR = "REEMPLAZAR"


def clave_actual() -> str:
    """La clave configurada, o cadena vacía si no hay ninguna válida.

    Se mira primero la variable de entorno: es la que tiene prioridad al
    cargar la configuración, así que ignorarla haría que a alguien que la
    tiene puesta se le siguiera pidiendo la clave una y otra vez.
    """
    del_entorno = (os.environ.get("ANTHROPIC_API_KEY") or "").strip()
    if del_entorno and MARCADOR not in del_entorno:
        return del_entorno

    if not DESTINO.exists():
        return ""
    for linea in DESTINO.read_text(encoding="utf-8", errors="ignore").splitlines():
        linea = linea.strip()
        if linea.startswith("#") or "=" not in linea:
            continue
        nombre, _, valor = linea.partition("=")
        if nombre.strip() == "ANTHROPIC_API_KEY":
            valor = valor.strip().strip('"').strip("'")
            if valor and MARCADOR not in valor:
                return valor
    return ""


def abrir(ruta: Path) -> bool:
    """Abre el archivo en un editor de texto. Devuelve si lo consiguió."""
    try:
        if sys.platform == "darwin":
            return subprocess.run(["open", "-e", str(ruta)]).returncode == 0
        if os.name == "nt":
            os.startfile(str(ruta))  # noqa: S606
            return True
        return subprocess.run(["xdg-open", str(ruta)]).returncode == 0
    except Exception:  # noqa: BLE001 - si no se puede, se indica la ruta
        return False


def guardar_clave(clave: str) -> None:
    """Escribe la clave en .env, respetando el resto del archivo."""
    if not DESTINO.exists() and PLANTILLA.exists():
        DESTINO.write_text(PLANTILLA.read_text(encoding="utf-8"), encoding="utf-8")

    lineas = (
        DESTINO.read_text(encoding="utf-8", errors="ignore").splitlines()
        if DESTINO.exists() else []
    )
    puesta = False
    for i, linea in enumerate(lineas):
        if linea.strip().startswith("ANTHROPIC_API_KEY"):
            lineas[i] = f"ANTHROPIC_API_KEY={clave}"
            puesta = True
            break
    if not puesta:
        lineas.append(f"ANTHROPIC_API_KEY={clave}")

    DESTINO.write_text("\n".join(lineas) + "\n", encoding="utf-8")
    os.environ["ANTHROPIC_API_KEY"] = clave  # vale ya, sin reiniciar


def asegurar_clave() -> bool:
    """Se asegura de que haya una clave, pidiéndola aquí mismo si falta.

    Pedirla en la propia ventana evita depender de que el editor de texto se
    abra al frente: en Mac se abre detrás de la Terminal y parece que no pasó
    nada. Devuelve False sólo si el cliente decide no ponerla ahora.
    """
    if clave_actual():
        return True

    print()
    print("  " + "=" * 64)
    print("  FALTA TU CLAVE DE CLAUDE")
    print("  " + "=" * 64)
    print()
    print("  La creas en  console.anthropic.com  →  Settings  →  API keys")
    print("  Empieza con  sk-ant-")
    print()
    print("  Cópiala y pégala aquí abajo:")
    print("    · en Mac se pega con  Command + V")
    print("    · en Windows, con clic derecho sobre la ventana")
    print()

    for intento in range(3):
        try:
            clave = input("  Pega tu clave y presiona ENTER: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return False

        clave = clave.strip().strip('"').strip("'")
        if not clave:
            print("  No pegaste nada. Inténtalo otra vez.\n")
            continue
        if not clave.startswith("sk-ant-"):
            print("  Esa no parece una clave de Claude: tiene que empezar")
            print("  con  sk-ant-  . Revisa que la copiaste completa.\n")
            continue

        guardar_clave(clave)
        print()
        print("  ✓ Clave guardada. No hace falta que la vuelvas a poner.")
        print()
        return True

    print()
    print("  Lo dejamos para después. Vuelve a abrir este mismo archivo")
    print("  cuando tengas la clave a mano.")
    print()
    return False


def main(argv: list[str] | None = None) -> int:
    print()
    print("=" * 66)
    print("  TU CLAVE DE CLAUDE")
    print("=" * 66)

    if not DESTINO.exists():
        if not PLANTILLA.exists():
            print("\n  [X] Falta .env.example. Vuelve a descargar el programa.\n")
            return 1
        DESTINO.write_text(
            PLANTILLA.read_text(encoding="utf-8"), encoding="utf-8"
        )
        print("\n  Se creó el archivo de configuración.")

    actual = clave_actual()
    if actual:
        print(f"\n  Ya tienes una clave puesta: {actual[:14]}…{actual[-4:]}")
        print("  No hace falta que hagas nada más en este paso.")
        print("\n  Si quieres cambiarla, el archivo está en:")
        print(f"      {DESTINO}")
        print()
        return 0

    # Se pide aquí mismo. Sólo si prefiere editarlo a mano se abre el editor.
    if asegurar_clave():
        return 0

    print("  Si prefieres escribirla en el archivo a mano, está en:")
    print(f"      {DESTINO}")
    if abrir(DESTINO):
        print()
        print("  Se abrió el editor. Si no lo ves, búscalo con Command + Tab:")
        print("  a veces se abre DETRÁS de esta ventana.")
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
