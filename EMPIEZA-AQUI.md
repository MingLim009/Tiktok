# Empieza aquí

Hola Adderly. Esto es el agente que responde automáticamente los mensajes de
tu bandeja de TikTok.

**No necesitas saber programar ni escribir comandos.** Todo se hace con doble
clic en los archivos que terminan en `.cmd`.

---

## Paso 1 — Preparar el programa y ver tus tasas

Doble clic en **`probar.cmd`**

La primera vez se demora un par de minutos preparándose. Es normal y pasa una
sola vez. Cuando termine, te muestra tus tasas de hoy, leídas directamente de
tu hoja "TASAS FINALES", con ejemplos de cotización.

Si ves tus tasas ahí, el motor de cálculo está funcionando bien.

---

## Paso 2 — Tu clave de Claude

En la carpeta hay un archivo llamado `.env.example`. Haz una copia y ponle de
nombre `.env` (así, con el punto adelante y sin nada más).

> Si Windows no te deja renombrarlo: abre el Bloc de notas, copia adentro todo
> el contenido de `.env.example`, y usa **Archivo → Guardar como** escribiendo
> el nombre entre comillas: `".env"`. Las comillas evitan que Windows le
> agregue `.txt` al final.

Ábrelo y pon tu clave en la línea que dice `ANTHROPIC_API_KEY`.

---

## Paso 3 — Conversar con el bot

Doble clic en **`conversar-con-el-bot.cmd`**

Escríbele como si fueras un cliente tuyo:

- `a cuánto está el cambio?`
- `quiero cambiar 5000 bolivianos a soles`
- `y si son 300 mil?`
- `hasta qué hora atienden?`
- `me pueden llamar?`

En la última te va a pedir tu número de teléfono y recién ahí pasa la
conversación a un asesor.

---

## Paso 4 — Conectar tu cuenta de TikTok

Doble clic en **`conectar-tiktok.cmd`**

Se abre una ventana de navegador. Ahí inicias sesión tú mismo, con tu cuenta
de siempre. TikTok te va a mandar un código a tu correo.

Esto se hace **una sola vez**. Tu contraseña no pasa por el programa.

---

## Paso 5 — Ver qué respondería, sin enviar nada

Doble clic en **`revisar-bandeja.cmd`**

Lee tus mensajes reales y te muestra en pantalla qué le respondería a cada
uno. **No envía nada.** Tus clientes no reciben ningún mensaje.

Si algo no funciona, doble clic en **`diagnostico.cmd`** y manda el archivo
`diagnostico_bandeja.txt` que queda en la carpeta.

---

## El día a día

Doble clic en **`estado.cmd`**

Te muestra de dónde salen las tasas hoy, cuántos mensajes se enviaron, y sobre
todo **quiénes están esperando que un asesor los llame**, con su teléfono y el
horario que prefieren.

---

## Lo que puedes cambiar tú mismo

Se editan con el Bloc de notas. Guardas y listo.

- **`config/negocio.yaml`** — horario, tono, preguntas frecuentes, cuándo pasar
  a una persona
- **`config/tasas.yaml`** — montos mínimos y de dónde salen las tasas
- **`config/live.yaml`** — palabras clave del Live y los mensajes que se envían

Cada archivo está comentado en español, línea por línea.

**Ejemplo:** para atender hasta las 6 de la tarde, en `config/negocio.yaml`
busca `cierre: "17:00"` y cámbialo por `"18:00"`.

### Las tasas se actualizan solas

El bot lee tu Google Sheet cada 5 minutos. **Si tú cambias una tasa en la hoja,
el bot ya responde con la nueva.** Nadie tiene que copiar nada a mano.

Si algún día la hoja no está disponible, usa una tasa de respaldo conservadora
y lo deja anotado, en vez de quedarse sin responder.

---

## Si quieres profundizar

- **`docs/INSTALACION.md`** — instalación paso a paso
- **`docs/USO.md`** — cómo cambiar cada cosa, con ejemplos
- **`docs/SEGURIDAD.md`** — riesgos, límites de envío y buenas prácticas

**Lee `docs/SEGURIDAD.md` antes de activar el envío real.** Explica de forma
directa el riesgo de que TikTok limite la cuenta y cómo lo reducimos.

---

## Si algo falla

Manda una captura de la ventana completa, con todo lo que aparezca en ella.
Con eso ubico el problema rápido.
