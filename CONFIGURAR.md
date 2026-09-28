# Poner en marcha el publicador (una sola vez, unos 20 minutos)

Hay tres cosas que solo puedes hacer tú, porque piden tu contraseña o tu permiso: crear el repositorio en GitHub, crear la app en Meta y pegar la clave en GitHub. Todo lo demás ya está hecho.

## 1. Crear el repositorio en GitHub (2 minutos)

1. Entra en <https://github.com/new> con tu cuenta.
2. Nombre del repositorio: `bomberoflash-publicador`.
3. Marca **Public**. Instagram necesita poder descargar las imágenes, y los secretos siguen siendo privados aunque el repositorio sea público.
4. No marques README, .gitignore ni licencia. Pulsa **Create repository**.
5. Avisa a Claude: sube él el código. Si GitHub te abre una ventana para autorizar, acéptala.

## 2. Crear la app en Meta y sacar el token (10-15 minutos)

La cuenta @bombero_flash ya es profesional (Metricool la usa), así que vale tal cual. Meta cambia los nombres de los menús de vez en cuando; si algo no coincide exactamente, busca el más parecido.

1. Entra en <https://developers.facebook.com/apps> con tu cuenta de Facebook. Si es la primera vez, te pedirá registrarte como desarrollador; es gratis.
2. Pulsa **Crear app**.
3. Nombre: `BomberoFlash Publicador`. Correo: el tuyo.
4. Caso de uso: **Gestionar mensajes y contenido en Instagram** (en inglés, *Manage messaging & content on Instagram*). Crea la app.
5. En el panel de la app, entra en **Casos de uso › Instagram › Configuración de la API con inicio de sesión para empresas de Instagram** (*API setup with Instagram business login*).
6. En **Generar tokens de acceso**, pulsa **Añadir cuenta**, entra con @bombero_flash y acepta los permisos, sobre todo **instagram_business_content_publish**.
   - Si te pide añadir la cuenta como **tester de Instagram**: en **Roles de la app › Roles › Testers de Instagram** añade `bombero_flash`. Después acepta la invitación desde Instagram en la web: **Configuración › Apps y sitios web › Invitaciones de tester**.
7. Junto a la cuenta verás su **ID de Instagram** (un número largo) y un botón **Generar token**. Copia las dos cosas en un sitio seguro. **No las mandes por el chat.**

La app puede quedarse en **modo desarrollo**: como la cuenta es tuya y eres administrador, no hace falta que Meta la revise. Si alguna vez Meta pidiera revisión, la publicación sigue por Metricool mientras tanto.

## 3. Guardar el token en GitHub (2 minutos)

En el repositorio `bomberoflash-publicador`: **Settings › Secrets and variables › Actions › New repository secret**. Crea estos secretos:

| Nombre | Valor |
|---|---|
| `IG_ACCESS_TOKEN` | el token del paso 2 |
| `IG_USER_ID` | el ID de Instagram del paso 2 |

Opcional, para que el token se renueve y se guarde solo, sin que tengas que tocar nada cada 60 días:

1. Entra en <https://github.com/settings/personal-access-tokens/new>.
2. Nombre `renovar token instagram`, caducidad la máxima.
3. En **Repository access** elige solo `bomberoflash-publicador`.
4. En **Permissions › Repository permissions**, pon **Secrets** en *Read and write*.
5. Genera el token y guárdalo como tercer secreto con el nombre `GH_PAT`.

Sin `GH_PAT` funciona igual. Cada lunes el sistema renueva el token en Instagram, y si algún día caducara, GitHub te manda un correo y generas uno nuevo en el paso 2.7.

## 4. Probar (1 minuto)

1. En el repositorio, pestaña **Actions**. Si te pregunta, pulsa **I understand my workflows, go ahead and enable them**.
2. Abre **Publicar en Instagram › Run workflow**, elige el modo **comprobar** y pulsa **Run workflow**.
3. Al terminar, abre la ejecución. Debe poner «Token válido para @bombero_flash» y cuántos posts hay en la cola.

A partir de ahí, cada hora comprueba la cola y publica lo que toque, aunque tengas el ordenador apagado.
