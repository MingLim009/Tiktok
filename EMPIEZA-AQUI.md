# Empieza aquí

Hola Adderly. Esto es el agente de atención automática para TikTok.
Esta hoja es para que veas funcionando lo principal en 2 minutos, sin
tener que entender nada de programación.

---

## Lo más rápido: ver las tasas

Haz **doble clic** en:

- **`probar.cmd`** si usas Windows
- **`probar.sh`** si usas Mac

La primera vez se demora un par de minutos preparando todo (te va avisando
en pantalla). Después abre una ventana negra y te muestra las tasas de hoy
leídas de tu propio Google Sheet, con ejemplos de cotización.

Si eso te aparece, el motor de tasas está funcionando correctamente.

---

## Conversar con el bot

En la misma ventana, cuando termine, escribe:

```
python -m ragnar_agent.cli.demo
```

Y escríbele como si fueras un cliente tuyo:

- `a cuánto está el cambio?`
- `quiero cambiar 5000 bolivianos a soles`
- `y si son 300 mil?`
- `hasta qué hora atienden?`
- `me pueden llamar por teléfono?`

En la última va a pasar la conversación a un asesor. En las otras responde solo.

> Para esto hace falta la clave de Claude en el archivo `.env`.
> Lo configuramos juntos en la sesión de conexión.

---

## Lo que puedes cambiar tú mismo

Todo esto se edita con el Bloc de notas, sin tocar programación.
Guardas el archivo, reinicias el bot y ya.

| Archivo | Qué cambias ahí |
|---|---|
| `config/negocio.yaml` | Horario, tono, preguntas frecuentes, cuándo pasar a una persona |
| `config/tasas.yaml` | Tramos por monto, montos mínimos, de dónde salen las tasas |
| `config/live.yaml` | Palabras clave del Live y los mensajes que se envían |

Cada archivo está comentado en español, línea por línea.

**Ejemplo** — para que el bot atienda hasta las 6 de la tarde, en
`config/negocio.yaml` busca:

```yaml
  cierre: "17:00"
```

y cámbialo a `"18:00"`. Eso es todo.

---

## Las tasas se actualizan solas

El bot lee tu Google Sheet cada 5 minutos. **Si tú actualizas la hoja, el bot
ya responde con la tasa nueva.** Nadie tiene que copiar nada a mano.

Si algún día la hoja no está disponible, usa una tasa de respaldo y lo deja
anotado, en vez de quedarse sin responder.

---

## Si quieres profundizar

| Documento | Para qué |
|---|---|
| `docs/INSTALACION.md` | Instalación paso a paso |
| `docs/USO.md` | Cómo cambiar cada cosa, con ejemplos |
| `docs/SEGURIDAD.md` | Riesgos, límites de envío y buenas prácticas |

**Lee `docs/SEGURIDAD.md` antes de activar el envío real.** Explica de forma
directa el riesgo de que TikTok limite la cuenta y cómo lo reducimos.

---

## ¿Algo no funciona?

Escríbeme y lo vemos. Si la ventana negra muestra un error, mándame una
captura de pantalla completa — con eso ubico el problema rápido.
