# Publicador de BomberoFlash para Instagram

Publica solo en @bombero_flash los carruseles y posts que hay en `cola.json`, a la hora indicada, sin Metricool y sin límite de 20 al mes. Usa la API oficial de Instagram, que permite hasta 100 publicaciones cada 24 horas y carruseles de hasta 10 imágenes.

Para ponerlo en marcha, sigue [CONFIGURAR.md](CONFIGURAR.md) (una sola vez).

## Cómo funciona

- `cola.json` guarda cada post: fecha y hora (hora de Madrid), imágenes, texto y estado (`pendiente`, `publicado` o `error`).
- `media/` guarda las imágenes en JPEG, que es el único formato que acepta Instagram por esta vía.
- `.github/workflows/publicar.yml` se ejecuta cada hora en los servidores de GitHub, publica el post que toque y apunta en `cola.json` que ya salió, con su enlace.
- `.github/workflows/renovar-token.yml` renueva cada lunes el token de Instagram, que dura 60 días.
- Si el publicador estuvo parado y hay posts atrasados, no los suelta todos de golpe: saca uno cada 20 horas.
- Si un post falla 3 veces, queda marcado como `error` con el motivo, y GitHub te avisa por correo.

## Uso diario

- **Añadir más posts:** pásale a Claude fotos y JSON de exámenes. Él genera los carruseles y los añade con `herramientas/anadir_a_cola.py`.
- **Ver qué se ha publicado:** en `cola.json`, o en la pestaña **Actions** de GitHub.
- **Pausar:** **Actions › Publicar en Instagram › ··· › Disable workflow**. Para volver a activarlo, **Enable workflow**.
- **Probar sin publicar:** **Actions › Publicar en Instagram › Run workflow**, modo **simular**.
- `herramientas/preguntas_usadas.json` lleva la lista de preguntas ya publicadas o programadas, para no repetir ninguna.

## Calendario cargado

Del 18 de octubre al 13 de noviembre de 2026:
- 10:00: 12 carruseles de exámenes oficiales de Navarra y 5 frases.
- 18:00: los 14 apuntes que Metricool ya no pudo publicar en octubre por el límite de 20 posts al mes del plan gratuito (tetraedro, RCP, EBEP, panel naranja, entidades locales, triaje, rollover, Constitución, diferencial, motobombas, Glasgow, Diputación, presión y extintores).

Las ejecuciones automáticas ya están activas: mientras falte el token de Instagram terminan sin hacer nada. En cuanto se guarde el secreto `IG_ACCESS_TOKEN` (CONFIGURAR.md) empieza a publicar. Si el token llega tarde, los posts atrasados salen de uno en uno cada 20 h.
