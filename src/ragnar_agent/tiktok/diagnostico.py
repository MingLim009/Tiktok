"""Diagnóstico de selectores: qué encuentra el bot y qué hay realmente.

Cuando TikTok cambia su interfaz, la bandeja deja de leerse. Volcar el HTML
sirve de poco en medio de una llamada con el cliente. Esto hace dos cosas:

  1. Prueba cada selector configurado y dice cuántos elementos encontró.
  2. Recorre la página y propone candidatos — sobre todo los atributos
     `data-e2e`, que es como TikTok marca sus componentes.

Con eso, arreglar un selector roto pasa de leer HTML a copiar una línea.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ..logging_setup import get_logger
from . import dm

log = get_logger(__name__)

# Qué selector cumple qué papel. Los nombres coinciden con las constantes
# de dm.py para que el informe diga exactamente qué editar.
GRUPOS: dict[str, tuple[str, list[str]]] = {
    "Lista de conversaciones": ("SEL_LISTA_CONVERSACIONES", dm.SEL_LISTA_CONVERSACIONES),
    "Nombre en cada fila": ("SEL_NOMBRE_EN_ITEM", dm.SEL_NOMBRE_EN_ITEM),
    "Vista previa del último mensaje": ("SEL_PREVIEW_EN_ITEM", dm.SEL_PREVIEW_EN_ITEM),
    "Marca de no leído": ("SEL_NO_LEIDO", dm.SEL_NO_LEIDO),
    "Burbujas del chat": ("SEL_BURBUJAS", dm.SEL_BURBUJAS),
    "Caja de texto": ("SEL_CAJA_TEXTO", dm.SEL_CAJA_TEXTO),
    "Botón de enviar": ("SEL_BOTON_ENVIAR", dm.SEL_BOTON_ENVIAR),
}

# Palabras que sugieren para qué sirve un data-e2e desconocido.
PISTAS = {
    "lista": ("list", "item", "conversation", "chat-list"),
    "nombre": ("nickname", "name", "user", "title"),
    "mensaje": ("msg", "message", "chat-item", "bubble", "content"),
    "no leído": ("unread", "badge", "dot", "count"),
    "escribir": ("input", "editor", "textbox", "compose"),
    "enviar": ("send", "submit"),
}


@dataclass
class Resultado:
    grupo: str
    constante: str
    encontrados: list[tuple[str, int]] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return any(n > 0 for _, n in self.encontrados)


def probar_selectores(page: Any) -> list[Resultado]:
    """Prueba cada selector configurado y cuenta lo que encuentra."""
    salida: list[Resultado] = []
    for grupo, (constante, selectores) in GRUPOS.items():
        r = Resultado(grupo=grupo, constante=constante)
        for sel in selectores:
            try:
                r.encontrados.append((sel, page.locator(sel).count()))
            except Exception:  # noqa: BLE001 - selector inválido en esta vista
                r.encontrados.append((sel, -1))
        salida.append(r)
    return salida


def descubrir_data_e2e(page: Any) -> list[tuple[str, int]]:
    """Todos los `data-e2e` de la página, con cuántas veces aparece cada uno.

    Es la pista más útil: TikTok marca sus componentes con este atributo, así
    que la lista suele contener el selector nuevo tal cual hay que escribirlo.
    """
    try:
        valores = page.evaluate(
            """() => {
                const cuenta = {};
                document.querySelectorAll('[data-e2e]').forEach(el => {
                    const v = el.getAttribute('data-e2e');
                    cuenta[v] = (cuenta[v] || 0) + 1;
                });
                return cuenta;
            }"""
        )
    except Exception as exc:  # noqa: BLE001
        log.warning("No se pudieron leer los data-e2e: %s", exc)
        return []
    return sorted(valores.items(), key=lambda kv: (-kv[1], kv[0]))


def descubrir_editables(page: Any) -> list[str]:
    """Dónde se puede escribir: candidatos para la caja de texto."""
    try:
        return page.evaluate(
            """() => {
                const sel = [];
                document.querySelectorAll(
                    "[contenteditable='true'],[contenteditable='plaintext-only'],textarea,[role='textbox']"
                ).forEach(el => {
                    const e2e = el.getAttribute('data-e2e');
                    if (e2e) sel.push(`[data-e2e='${e2e}']`);
                    else if (el.id) sel.push(`#${el.id}`);
                    else sel.push(el.tagName.toLowerCase() +
                        (el.getAttribute('role') ? `[role='${el.getAttribute('role')}']` : ''));
                });
                return [...new Set(sel)];
            }"""
        )
    except Exception:  # noqa: BLE001
        return []


def _sugerir(valor: str) -> str:
    v = valor.lower()
    for papel, claves in PISTAS.items():
        if any(k in v for k in claves):
            return papel
    return ""


def informe(page: Any) -> str:
    """Informe en texto, pensado para leerse en medio de una llamada."""
    lineas: list[str] = []
    add = lineas.append

    add("=" * 70)
    add("  DIAGNÓSTICO DE LA BANDEJA")
    add("=" * 70)
    add(f"  URL: {getattr(page, 'url', '?')}")
    add("")

    resultados = probar_selectores(page)
    rotos = [r for r in resultados if not r.ok]

    add("  SELECTORES ACTUALES")
    add("  " + "-" * 66)
    for r in resultados:
        estado = "OK " if r.ok else "!! "
        add(f"  [{estado}] {r.grupo}")
        for sel, n in r.encontrados:
            marca = "·" if n > 0 else ("x" if n == 0 else "?")
            cuenta = f"{n} elemento(s)" if n >= 0 else "selector inválido"
            add(f"          {marca} {cuenta:<18} {sel}")
    add("")

    if not rotos:
        add("  Todos los selectores encuentran algo. Si aun así falla la")
        add("  lectura, el problema está en la lógica, no en los selectores.")
        add("")
        return "\n".join(lineas)

    add("  " + "=" * 66)
    add(f"  HAY {len(rotos)} GRUPO(S) SIN RESULTADOS — hay que actualizarlos")
    add("  " + "=" * 66)
    for r in rotos:
        add(f"    · {r.grupo}  →  editar {r.constante} en tiktok/dm.py")
    add("")

    e2e = descubrir_data_e2e(page)
    if e2e:
        add("  CANDIDATOS ENCONTRADOS EN LA PÁGINA (atributos data-e2e)")
        add("  Copia el selector de la izquierda al grupo que corresponda.")
        add("  " + "-" * 66)
        for valor, n in e2e[:35]:
            pista = _sugerir(valor)
            sufijo = f"  ← ¿{pista}?" if pista else ""
            add(f"    [data-e2e='{valor}']".ljust(48) + f"{n:>3}x{sufijo}")
        if len(e2e) > 35:
            add(f"    … y {len(e2e) - 35} más")
        add("")

    editables = descubrir_editables(page)
    if editables:
        add("  DÓNDE SE PUEDE ESCRIBIR (candidatos para la caja de texto)")
        add("  " + "-" * 66)
        for sel in editables[:10]:
            add(f"    {sel}")
        add("")

    add("  Cómo se arregla:")
    add("    1. Abre src/ragnar_agent/tiktok/dm.py")
    add("    2. Busca la constante que dice el informe")
    add("    3. Agrega el selector candidato AL PRINCIPIO de esa lista")
    add("    4. Vuelve a correr con --diagnostico para confirmar")
    add("")
    return "\n".join(lineas)
