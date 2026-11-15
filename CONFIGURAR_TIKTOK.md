# Conectar TikTok al publicador (una sola vez, unos 30 minutos)

El publicador sube a TikTok los mismos reels y carruseles que publica en Instagram, a la misma hora, con la API oficial de TikTok. Es gratis: no usa Metricool ni ningún programa de pago. Las historias no se suben, porque TikTok no las admite por la API.

Hay cosas que solo puedes hacer tú porque piden tu contraseña: activar la web del repositorio, crear la app en TikTok y guardar las claves en GitHub. **Ninguna clave se manda por el chat.**

## Cómo publica, según cómo esté la app

| Situación de la app de TikTok | Qué pasa a la hora programada |
|---|---|
| Recién creada (modo **borrador**, el que viene puesto) | El post llega a tu **bandeja de TikTok** en el móvil (notificación «Tu contenido está listo»). Lo abres, si quieres le pones una música de moda, y pulsas **Publicar**. Un toque por post. |
| Aprobada por TikTok (auditoría de *Direct Post*) | Pones la variable `TIKTOK_MODO` en `directo` y se publica solo, sin tocar nada. |

TikTok obliga a esa revisión para publicar en público sin intervención. Mientras no la apruebe, cualquier publicación directa saldría como «Solo yo», por eso el modo borrador es el que viene puesto.

## 1. Activar la web del repositorio (2 minutos)

TikTok descarga las fotos de los carruseles desde una dirección que tiene que ser tuya y verificada. Sirve la web gratuita de GitHub:

1. En el repositorio `bomberoflash-publicador`: **Settings › Pages**.
2. En **Source** elige **Deploy from a branch**, rama **main**, carpeta **/ (root)**. Pulsa **Save**.
3. A los dos minutos abre <https://angelfernandezmartinez9-glitch.github.io/bomberoflash-publicador/tiktok/>: debe salir «Conectar TikTok con el publicador».

## 2. Crear la app en TikTok for Developers (15 minutos)

TikTok cambia los menús a menudo; si algo no coincide, busca el nombre más parecido.

1. Entra en <https://developers.tiktok.com> con la cuenta de TikTok donde quieres publicar y regístrate como desarrollador (gratis).
2. **Manage apps › Connect an app**. Tipo: *Individual*.
3. Ficha de la app:
   - Nombre: `BomberoFlash Publicador`. Icono: el logo de BomberoFlash. Categoría: *Education*.
   - Descripción: «Herramienta privada para publicar a la hora programada el contenido propio de BomberoFlash (oposiciones a bombero) en mi cuenta de TikTok.»
   - **Terms of Service URL**: `https://angelfernandezmartinez9-glitch.github.io/bomberoflash-publicador/legal/terminos.html`
   - **Privacy Policy URL**: `https://angelfernandezmartinez9-glitch.github.io/bomberoflash-publicador/legal/privacidad.html`
   - Plataforma: **Web**, con la dirección `https://angelfernandezmartinez9-glitch.github.io/bomberoflash-publicador/`.
4. **Products › Add products**: añade **Login Kit** y **Content Posting API**.
   - En Login Kit, **Redirect URI**: `https://angelfernandezmartinez9-glitch.github.io/bomberoflash-publicador/tiktok/` (con la barra final).
   - En Content Posting API, activa **Direct Post**.
5. **Scopes**: marca `user.info.basic`, `video.upload` y `video.publish`.
6. **URL properties › Verify**: elige *URL prefix* y pon `https://angelfernandezmartinez9-glitch.github.io/bomberoflash-publicador/`. TikTok te da un archivo `.txt` para descargar. Súbelo a la raíz del repositorio (**Add file › Upload files** en GitHub) o pásaselo a Claude, que lo sube él (no es secreto). Cuando esté publicado, pulsa **Verify**.
7. Para empezar ya, sin esperar a TikTok: pestaña **Sandbox › Create sandbox**, y en **Target users** añade tu cuenta de TikTok. Usa la *Client key* y el *Client secret* del sandbox.
8. Cuando quieras que se publique solo: **Submit for review** de la app y, una vez aprobada, la **auditoría de Content Posting API** (formulario en la página del producto). Al aprobarla, usa las claves de producción (paso 3) y pon `TIKTOK_MODO` en `directo`.

## 3. Guardar las claves en GitHub (3 minutos)

En el repositorio: **Settings › Secrets and variables › Actions › New repository secret**.

| Nombre | Valor |
|---|---|
| `TIKTOK_CLIENT_KEY` | *Client key* de la app (o del sandbox) |
| `TIKTOK_CLIENT_SECRET` | *Client secret* de la app (o del sandbox) |
| `GH_PAT` | solo si no lo creaste ya para Instagram: mira el apartado opcional del paso 3 de CONFIGURAR.md |

`GH_PAT` aquí sí hace falta: es lo que deja al publicador guardar la clave de tu cuenta de TikTok y renovarla sola.

## 4. Conectar tu cuenta (2 minutos)

1. Abre <https://angelfernandezmartinez9-glitch.github.io/bomberoflash-publicador/tiktok/>.
2. Pega la *Client key* y pulsa **Conectar con TikTok**. Entra con tu cuenta y acepta.
3. Te devuelve a la página con un código. Cópialo.
4. En GitHub: **Actions › Conectar TikTok › Run workflow**, pega el código y pulsa **Run workflow**. Tiene que acabar en verde y decir «TikTok conectado: @tucuenta».

## 5. Probar

**Actions › Publicar en Instagram y TikTok › Run workflow**, modo **comprobar**. Debe decir con qué cuenta está conectado TikTok y cuántos posts tiene en cola. A partir de ahí, cada 15 minutos sube lo que toque.

## Si algo falla

- El estado de cada post en TikTok queda en `cola.json`, en el apartado `tiktok` de cada post (`en_bandeja`, `publicado` o `error` con el motivo). Tras 3 fallos se deja de intentar y GitHub te avisa por correo.
- Si TikTok cambia la clave y no hay `GH_PAT`, sale un aviso: repite el paso 4.
- Si el publicador estuvo parado en modo directo, los atrasados salen de uno en uno cada 6 horas. En modo borrador van a la bandeja y tú decides cuándo publicarlos.
