"""Demo en la terminal — el bot sin TikTok de por medio.

    python -m ragnar_agent.cli.demo            # chat con el agente
    python -m ragnar_agent.cli.demo --tasas    # sólo muestra las tasas de hoy

Sirve para probar respuestas, tono y cotizaciones antes de conectar la cuenta,
y para enseñarle al cliente cómo va a responder el bot.
"""

from __future__ import annotations

import argparse
import os
import sys
import time

from ..config import get_settings
from ..logging_setup import get_logger, setup
from ..rates import get_motor
from ..rates.engine import RequiereAsesor

log = get_logger(__name__)

EJEMPLOS = [
    "hola, a cuánto está el cambio?",
    "quiero cambiar 5000 bolivianos a soles",
    "y si cambio 300000 bs?",
    "hasta qué hora atienden?",
    "me puedes llamar por teléfono?",
]


def cuenta_regresiva(segundos: int) -> None:
    """Espera antes de empezar, para poder darle a grabar sin prisa.

    Al terminar limpia la pantalla, así el video arranca con la terminal
    vacía y no se ve el propio contador.
    """
    if segundos <= 0:
        return

    print()
    print("  ┌────────────────────────────────────────────┐")
    print("  │  Pulsa AHORA el botón de grabar.           │")
    print("  │  La demo arranca sola en unos segundos.    │")
    print("  └────────────────────────────────────────────┘")
    print()

    for restante in range(segundos, 0, -1):
        print(f"\r     {restante}…   ", end="", flush=True)
        time.sleep(1)

    os.system("cls" if os.name == "nt" else "clear")


def mostrar_tasas() -> int:
    motor = get_motor()
    tasas = motor.tasas_crudas()

    print()
    print("=" * 66)
    print("  TASAS VIGENTES — Ragnar Capital")
    print("=" * 66)
    print(f"  Fuente: {tasas.fuente}   Fecha en la hoja: {tasas.fecha or 'n/d'}")
    print()

    if tasas.tablas:
        for nombre, tabla in sorted(tasas.tablas.items()):
            moneda = {"BOB": "bolivianos", "PEN": "soles"}.get(tabla.unidad, tabla.unidad)
            print(f"  {nombre}   (según el monto en {moneda})")
            for t in tabla.tramos:
                desde = f"{int(t.desde):,}".replace(",", " ")
                hasta = ("en adelante" if t.hasta is None
                         else f"{int(t.hasta):,}".replace(",", " "))
                print(f"      {desde:>9} – {hasta:<12} {t.tasa}")
            print()
    else:
        for clave, valor in tasas.valores.items():
            print(f"  {clave:<14} {valor}")
        print()

    print("  Ejemplos de cotización:")
    print("  " + "-" * 62)
    ejemplos = [
        ("bob_a_pen", 1000), ("bob_a_pen", 5_000), ("bob_a_pen", 300_000),
        ("pen_a_bob", 1000), ("pen_a_bob", 40_000),
        ("bob_a_usd_peru", 5_000), ("bob_a_usd_swift", 100_000),
    ]
    for operacion, monto in ejemplos:
        try:
            print(f"  {motor.cotizar(operacion, monto).texto()}")
        except RequiereAsesor as exc:
            print(f"  {operacion}: {exc}")
        except Exception as exc:  # noqa: BLE001
            print(f"  {operacion}: error — {exc}")

    print()
    for nombre, op in motor._ops.items():  # noqa: SLF001
        if op.get("solo_derivar"):
            print(f"  {op.get('etiqueta', nombre)}: se deriva a un asesor "
                  f"(sin tasa automática todavía)")
    print()
    return 0


def chat() -> int:
    from . import crear_agente

    agente = crear_agente()
    if agente is None:
        return 2

    historial: list[dict[str, str]] = []

    print()
    print("=" * 66)
    print("  DEMO — Agente de Ragnar Capital")
    print("=" * 66)
    print("  Escribe como si fueras un cliente. 'salir' para terminar.")
    print()
    print("  Ideas para probar:")
    for e in EJEMPLOS:
        print(f"    · {e}")
    print()

    while True:
        try:
            entrada = input("  Cliente > ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return 0

        if not entrada:
            continue
        if entrada.lower() in {"salir", "exit", "quit"}:
            return 0

        try:
            respuesta = agente.responder(entrada, historial)
        except Exception as exc:  # noqa: BLE001
            log.exception("Error al generar la respuesta")
            print(f"  ✗ {exc}\n")
            continue

        print(f"  Bot     > {respuesta.texto}")
        for cot in respuesta.cotizaciones:
            print(f"            [tasa usada: {cot['tasa_aplicada']} · {cot['tramo']}]")
        if respuesta.derivar:
            print(f"            [⚑ DERIVADO A UN ASESOR — motivo: {respuesta.motivo}]")
        print()

        historial.append({"role": "user", "content": entrada})
        historial.append({"role": "assistant", "content": respuesta.texto})
        historial = historial[-16:]


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Demo del agente de Ragnar Capital")
    p.add_argument("--tasas", action="store_true",
                   help="Muestra las tasas y ejemplos (no necesita API key)")
    p.add_argument("--esperar", type=int, default=0, metavar="SEGUNDOS",
                   help="Cuenta atrás antes de empezar, para grabar la pantalla "
                        "(ejemplo: --esperar 5)")
    args = p.parse_args(argv)

    setup(get_settings().log_level)
    cuenta_regresiva(args.esperar)
    return mostrar_tasas() if args.tasas else chat()


if __name__ == "__main__":
    sys.exit(main())
