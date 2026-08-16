"""Panel de estado: qué está pendiente de atender y cómo van los límites.

    python -m ragnar_agent.cli.estado
    python -m ragnar_agent.cli.estado --reactivar USUARIO

Es el comando que se corre a diario para ver si hay clientes esperando a que
una persona los atienda.
"""

from __future__ import annotations

import argparse
import sys

from .. import config
from ..config import get_settings
from ..logging_setup import setup
from ..rates import get_motor
from ..safety import Limitador
from ..store import get_store


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Estado del agente de Ragnar Capital")
    p.add_argument("--reactivar", metavar="USUARIO",
                   help="Devuelve al bot una conversación que atendió una persona")
    args = p.parse_args(argv)

    setup("WARNING")  # panel limpio, sin ruido de logs
    store = get_store()

    if args.reactivar:
        usuario = args.reactivar.lstrip("@")
        thread_id = f"tiktok:{usuario}"
        store.marcar_estado(thread_id, "bot")
        print(f"\n  ✓ La conversación con @{usuario} vuelve a manos del bot.\n")
        return 0

    print()
    print("=" * 66)
    print("  ESTADO DEL AGENTE — Ragnar Capital")
    print("=" * 66)

    # -- tasas -------------------------------------------------------------
    print("\n  TASAS")
    try:
        tasas = get_motor().tasas_crudas()
        origen = {
            "google_sheet": "Google Sheet (en vivo)",
            "odoo": "Odoo",
            "manual": "respaldo manual ⚠",
        }.get(tasas.fuente, tasas.fuente)
        print(f"    Fuente: {origen}")
        print(f"    Fecha en la hoja: {tasas.fecha or 'sin fecha'}")
        for clave in ("RC. BOB/PEN", "RC. PEN/BOB"):
            if clave in tasas.valores:
                print(f"    {clave:<14} {tasas.valores[clave]}")
        if tasas.fuente == "manual":
            print("    ⚠ No se pudo leer la fuente en vivo; se está cotizando")
            print("      con las tasas de respaldo de config/tasas.yaml")
    except Exception as exc:  # noqa: BLE001
        print(f"    ✗ No se pudieron leer las tasas: {exc}")

    # -- límites de envío --------------------------------------------------
    limitador = Limitador(store, config.live().get("limites", {}))
    print("\n  ENVÍOS")
    print(f"    {limitador.resumen()}")

    # -- derivaciones ------------------------------------------------------
    pendientes = store.derivaciones_pendientes()
    print(f"\n  REUNIONES POR AGENDAR ({len(pendientes)})")
    if not pendientes:
        print("    Ninguna. El bot está resolviendo todo solo.")
    else:
        etiquetas = {
            "llamada": "pidió una llamada",
            "reunion": "pidió reunión / Meet",
            "peticion_explicita": "pidió hablar con una persona",
        }
        for d in pendientes:
            motivo = etiquetas.get(d["motivo"], d["motivo"])
            cuando = str(d["creado_en"]).replace("T", " ")
            telefono = (d.get("telefono") or "").strip()
            horario = (d.get("horario") or "").strip()

            print(f"\n    @{d['usuario']}  ·  {motivo}")
            print(f"      Teléfono : {telefono or '— no lo quiso dar —'}")
            print(f"      Prefiere : {horario or 'sin preferencia'}")
            print(f"      Pedido   : {cuando}")
            if d.get("resumen"):
                print(f"      {d['resumen']}")

    print()
    print("-" * 66)
    if pendientes:
        print("  Cuando un asesor ya atendió a alguien, devuélvele la")
        print("  conversación al bot con:")
        print(f"      python -m ragnar_agent.cli.estado --reactivar {pendientes[0]['usuario']}")
    else:
        print("  Sin pendientes.")
    print()

    if get_settings().dry_run:
        print("  Nota: DRY_RUN=true en .env — el bot NO está enviando mensajes.")
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
