"""Utilidades comunes de los comandos.

El cliente no programa: cualquier problema de configuración tiene que
explicarse en una frase, no en un traceback de Python. Un traceback lo lee
como "se rompió el programa" y no como "me falta pegar mi clave".
"""

from __future__ import annotations


def crear_agente():
    """Devuelve el agente de IA, o None explicando en claro qué falta."""
    try:
        from ..ai import AgenteIA

        return AgenteIA()
    except RuntimeError as exc:
        _aviso("FALTA CONFIGURAR TU CLAVE DE CLAUDE", str(exc))
        return None
    except Exception as exc:  # noqa: BLE001 - cualquier fallo debe ser legible
        _aviso(
            "NO SE PUDO INICIAR EL AGENTE",
            f"{exc}\n\nMándame una captura de esta ventana completa y lo reviso.",
        )
        return None


def _aviso(titulo: str, cuerpo: str) -> None:
    print()
    print("  " + "=" * 64)
    print(f"  {titulo}")
    print("  " + "=" * 64)
    for linea in cuerpo.splitlines():
        print(f"  {linea}" if linea.strip() else "")
    print()
