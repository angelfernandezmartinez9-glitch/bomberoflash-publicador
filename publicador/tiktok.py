#!/usr/bin/env python3
"""Publicador automático de BomberoFlash para TikTok.

Publica en TikTok los mismos reels y carruseles de cola.json que salen en Instagram,
a la misma hora, con la API oficial de TikTok (Content Posting API). Es gratis y solo
usa la librería estándar de Python.

Modos:
  python publicador/tiktok.py              publica lo que toque (por defecto)
  python publicador/tiktok.py --simular    enseña lo que publicaría, sin tocar TikTok
  python publicador/tiktok.py --comprobar  comprueba la conexión con la cuenta de TikTok
  python publicador/tiktok.py --conectar   cambia el código de autorización por la clave
                                           permanente (TIKTOK_CODIGO) y la deja en TOKEN_OUT

Qué se sube a TikTok:
  - reel                el vídeo, con el texto del post
  - imagen / carrusel   un post de fotos de TikTok (hasta 35 fotos)
  - historia            no: TikTok no tiene historias por la API
  Solo los posts con fecha desde "tiktok_desde" (en cola.json). Un post puede llevar
  "texto_tiktok" para usar otro texto, y "redes": ["tiktok"] para salir solo en TikTok.

Modo de publicación (variable TIKTOK_MODO):
  borrador   (por defecto) el post llega a la bandeja de TikTok del móvil y se publica
             con un toque. Funciona desde el primer día, sin que TikTok revise la app.
  directo    se publica solo. Necesita que TikTok haya aprobado la app (auditoría);
             antes de eso TikTok lo deja en privado («Solo yo»).

Variables de entorno:
  TIKTOK_CLIENT_KEY, TIKTOK_CLIENT_SECRET   de la app de TikTok for Developers
  TIKTOK_REFRESH_TOKEN                      clave permanente de la cuenta (la deja --conectar)
  TIKTOK_MODO                               borrador o directo
  TIKTOK_PRIVACIDAD                         en modo directo, por defecto PUBLIC_TO_EVERYONE
  TIKTOK_MEDIA_BASE_URL                     dirección pública verificada en TikTok donde están
                                            las fotos (por defecto, GitHub Pages del repositorio)
  TIKTOK_REDIRECT_URI                       la misma que en la app (por defecto, la página
                                            tiktok/ de GitHub Pages)
  TOKEN_OUT                                 fichero donde se escribe la clave nueva si cambia
"""
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from zoneinfo import ZoneInfo

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COLA = os.path.join(RAIZ, "cola.json")
API = "https://open.tiktokapis.com/v2"
MAX_INTENTOS = 3
MB = 1024 * 1024

# Línea que se pone en TikTok en lugar de «Comenta X y te mando…», porque el envío
# automático por privado (LinkDM) solo funciona en Instagram.
CTA_TIKTOK = "🔗 Prueba Bombero Flash gratis: tienes el enlace en mi perfil."


class ErrorTikTok(Exception):
    pass


# ---------------------------------------------------------------- llamadas a la API

def _peticion(url, datos=None, cabeceras=None, metodo=None, json_cuerpo=None):
    cabeceras = dict(cabeceras or {})
    if json_cuerpo is not None:
        datos = json.dumps(json_cuerpo).encode()
        cabeceras["Content-Type"] = "application/json; charset=UTF-8"
    peticion = urllib.request.Request(url, data=datos, headers=cabeceras, method=metodo)
    try:
        with urllib.request.urlopen(peticion, timeout=300) as r:
            cuerpo = r.read().decode() or "{}"
    except urllib.error.HTTPError as e:
        cuerpo = e.read().decode(errors="replace")
        raise ErrorTikTok(f"TikTok respondió {e.code}: {_detalle(cuerpo)}") from None
    try:
        respuesta = json.loads(cuerpo)
    except ValueError:
        return {}
    error = respuesta.get("error")
    if isinstance(error, dict) and error.get("code") not in (None, "", "ok"):
        raise ErrorTikTok(f"TikTok: {error.get('code')} · {error.get('message', '')}")
    if isinstance(error, str) and error:
        raise ErrorTikTok(f"TikTok: {error} · {respuesta.get('error_description', '')}")
    return respuesta


def _detalle(cuerpo):
    try:
        j = json.loads(cuerpo)
    except ValueError:
        return cuerpo[:300]
    e = j.get("error")
    if isinstance(e, dict):
        return f"{e.get('code')} · {e.get('message', '')}"
    return f"{e} · {j.get('error_description', '')}"


def pedir_token(**campos):
    """Pide a TikTok un token de acceso (con un código o con la clave permanente)."""
    clave = os.environ.get("TIKTOK_CLIENT_KEY", "").strip()
    secreto = os.environ.get("TIKTOK_CLIENT_SECRET", "").strip()
    if not clave or not secreto:
        raise ErrorTikTok("Faltan los secretos TIKTOK_CLIENT_KEY y TIKTOK_CLIENT_SECRET.")
    campos.update(client_key=clave, client_secret=secreto)
    return _peticion(f"{API}/oauth/token/", datos=urllib.parse.urlencode(campos).encode(),
                     cabeceras={"Content-Type": "application/x-www-form-urlencoded"}, metodo="POST")


def token_de_acceso():
    """Cambia la clave permanente por un token de 24 h. Si TikTok da una clave nueva, la guarda."""
    refresco = os.environ.get("TIKTOK_REFRESH_TOKEN", "").strip()
    if not refresco:
        raise ErrorTikTok("Falta el secreto TIKTOK_REFRESH_TOKEN (conecta la cuenta: CONFIGURAR_TIKTOK.md).")
    r = pedir_token(grant_type="refresh_token", refresh_token=refresco)
    nuevo = r.get("refresh_token", "")
    if nuevo and nuevo != refresco:
        _guardar_clave(nuevo)
    return r["access_token"]


def _guardar_clave(clave):
    salida = os.environ.get("TOKEN_OUT")
    if salida:
        with open(salida, "w", encoding="utf-8") as f:
            f.write(clave)


def api(token, ruta, cuerpo=None):
    r = _peticion(f"{API}/{ruta}", json_cuerpo=cuerpo if cuerpo is not None else {},
                  cabeceras={"Authorization": f"Bearer {token}"}, metodo="POST")
    return r.get("data", {})


# ---------------------------------------------------------------- textos y archivos

def texto_tiktok(post):
    """Texto del post para TikTok: el mismo que en Instagram, pero sin «Comenta X y te mando…»."""
    if post.get("texto_tiktok"):
        return post["texto_tiktok"].strip()
    lineas = post.get("texto", "").splitlines()
    salida, cambiado = [], False
    for linea in lineas:
        if re.search(r"(?i:\bcomenta)\s+[A-ZÁÉÍÓÚÑ0-9]{2,}\b", linea) and not re.search(r"comenta\s+a\s+o\s+b", linea, re.I):
            if not cambiado:
                salida.append(CTA_TIKTOK)
                cambiado = True
            continue
        salida.append(linea)
    texto = "\n".join(salida).strip()
    if not cambiado:
        texto = f"{texto}\n\n{CTA_TIKTOK}".strip()
    return texto


def recortar(texto, maximo):
    return texto if len(texto) <= maximo else texto[: maximo - 1].rstrip() + "…"


def titulo_y_descripcion(texto):
    """Un post de fotos lleva título (90 caracteres) y descripción (4.000)."""
    primera = texto.split("\n", 1)[0].strip()
    resto = texto.split("\n", 1)[1].strip() if "\n" in texto else ""
    if len(primera) <= 90:
        return primera, recortar(resto or primera, 4000)
    return recortar(primera, 90), recortar(texto, 4000)


def url_fotos(ruta):
    base = os.environ.get("TIKTOK_MEDIA_BASE_URL", "").strip()
    if not base:
        repo = os.environ.get("GITHUB_REPOSITORY", "")
        if "/" not in repo:
            raise ErrorTikTok("Falta TIKTOK_MEDIA_BASE_URL (la dirección pública verificada de las fotos).")
        dueno, nombre = repo.split("/", 1)
        base = f"https://{dueno.lower()}.github.io/{nombre}/"
    return base.rstrip("/") + "/" + urllib.parse.quote(ruta.lstrip("/"))


def modo():
    m = os.environ.get("TIKTOK_MODO", "borrador").strip().lower()
    return "directo" if m == "directo" else "borrador"


# ---------------------------------------------------------------- publicar

def subir_video(token, ruta_local, post):
    """Sube el vídeo por trozos (TikTok: trozos de 5 a 64 MB; si pesa menos de 64 MB, de una vez)."""
    tam = os.path.getsize(ruta_local)
    if tam <= 64 * MB:
        trozo, total = tam, 1
    else:
        trozo = 10 * MB
        total = tam // trozo
    fuente = {"source": "FILE_UPLOAD", "video_size": tam, "chunk_size": trozo, "total_chunk_count": total}
    if modo() == "directo":
        info = {
            "title": recortar(texto_tiktok(post), 2200),
            "privacy_level": os.environ.get("TIKTOK_PRIVACIDAD", "PUBLIC_TO_EVERYONE"),
            "disable_comment": False, "disable_duet": False, "disable_stitch": False,
            "is_aigc": bool(post.get("ia")),
        }
        datos = api(token, "post/publish/video/init/", {"post_info": info, "source_info": fuente})
    else:
        datos = api(token, "post/publish/inbox/video/init/", {"source_info": fuente})
    url_subida, publish_id = datos["upload_url"], datos["publish_id"]
    with open(ruta_local, "rb") as f:
        for i in range(total):
            inicio = i * trozo
            fin = tam - 1 if i == total - 1 else inicio + trozo - 1
            f.seek(inicio)
            pedazo = f.read(fin - inicio + 1)
            _peticion(url_subida, datos=pedazo, metodo="PUT", cabeceras={
                "Content-Type": "video/mp4",
                "Content-Length": str(len(pedazo)),
                "Content-Range": f"bytes {inicio}-{fin}/{tam}",
            })
    return publish_id


def subir_fotos(token, post):
    fotos = [url_fotos(r) for r in post["imagenes"]]
    if not 1 <= len(fotos) <= 35:
        raise ErrorTikTok("Un post de fotos de TikTok lleva entre 1 y 35 fotos.")
    titulo, descripcion = titulo_y_descripcion(texto_tiktok(post))
    info = {"title": titulo, "description": descripcion, "disable_comment": False, "auto_add_music": True}
    if modo() == "directo":
        info["privacy_level"] = os.environ.get("TIKTOK_PRIVACIDAD", "PUBLIC_TO_EVERYONE")
    cuerpo = {
        "post_info": info,
        "source_info": {"source": "PULL_FROM_URL", "photo_cover_index": 0, "photo_images": fotos},
        "post_mode": "DIRECT_POST" if modo() == "directo" else "MEDIA_UPLOAD",
        "media_type": "PHOTO",
    }
    return api(token, "post/publish/content/init/", cuerpo)["publish_id"]


def estado_envio(token, publish_id, espera=240):
    """Espera a que TikTok procese el envío. Devuelve el estado final o PROCESANDO."""
    inicio = time.time()
    while True:
        datos = api(token, "post/publish/status/fetch/", {"publish_id": publish_id})
        estado = datos.get("status", "")
        if estado == "FAILED":
            raise ErrorTikTok(f"TikTok no pudo procesarlo: {datos.get('fail_reason', 'sin motivo')}")
        if estado in ("PUBLISH_COMPLETE", "SEND_TO_USER_INBOX"):
            return estado
        if time.time() - inicio > espera:
            return "PROCESANDO"
        time.sleep(8)


def publicar_en_tiktok(token, post):
    if post.get("tipo") == "reel":
        ruta = os.path.join(RAIZ, post["video"])
        if not os.path.exists(ruta):
            raise ErrorTikTok(f"No encuentro el vídeo {post['video']}.")
        return subir_video(token, ruta, post)
    return subir_fotos(token, post)


# ---------------------------------------------------------------- cola

def cargar_cola():
    with open(COLA, encoding="utf-8") as f:
        return json.load(f)


def guardar_cola(cola):
    with open(COLA, "w", encoding="utf-8") as f:
        json.dump(cola, f, ensure_ascii=False, indent=2)
        f.write("\n")


def va_a_tiktok(post, cola):
    if post.get("tipo") == "historia" or post.get("estado") == "archivado":
        return False
    redes = post.get("redes")
    if redes is not None and "tiktok" not in redes:
        return False
    desde = cola.get("tiktok_desde")
    return bool(desde) and post["fecha"] >= desde


def pendientes_tiktok(cola):
    zona = ZoneInfo(cola.get("zona", "Europe/Madrid"))
    ahora = datetime.now(zona)
    listos = []
    for post in cola["posts"]:
        if not va_a_tiktok(post, cola):
            continue
        if post.get("tiktok", {}).get("estado", "pendiente") not in ("pendiente", "procesando"):
            continue
        fecha = datetime.strptime(post["fecha"], "%Y-%m-%d %H:%M").replace(tzinfo=zona)
        if fecha <= ahora:
            listos.append((fecha, post))
    listos.sort(key=lambda p: p[0])
    return [p for _, p in listos]


def hay_atraso_reciente(cola, listos):
    """En modo directo, si el primero lleva más de 2 h de retraso (el publicador estuvo parado o la
    cuenta sin conectar), sale uno cada 6 h para no soltar una tanda de golpe. En modo borrador no
    hace falta: van a la bandeja y tú decides cuándo publicarlos."""
    if modo() != "directo":
        return False
    zona = ZoneInfo(cola.get("zona", "Europe/Madrid"))
    ahora = datetime.now(zona)
    primero = datetime.strptime(listos[0]["fecha"], "%Y-%m-%d %H:%M").replace(tzinfo=zona)
    if (ahora - primero).total_seconds() < 2 * 3600:
        return False
    fechas = [datetime.fromisoformat(p["tiktok"]["enviado_en"]) for p in cola["posts"]
              if p.get("tiktok", {}).get("enviado_en")]
    return bool(fechas) and (ahora - max(fechas)).total_seconds() < 6 * 3600


def resumen(texto):
    print(texto)
    ruta = os.environ.get("GITHUB_STEP_SUMMARY")
    if ruta:
        with open(ruta, "a", encoding="utf-8") as f:
            f.write(texto + "\n")


def modo_publicar(simular=False):
    cola = cargar_cola()
    listos = pendientes_tiktok(cola)
    if not listos:
        resumen("TikTok: no hay nada que subir ahora.")
        return 0
    # Primero se miran los envíos que se quedaron procesando en la ejecución anterior.
    procesando = [p for p in listos if p.get("tiktok", {}).get("estado") == "procesando"]
    nuevos = [p for p in listos if p not in procesando]
    if nuevos and hay_atraso_reciente(cola, nuevos):
        resumen(f"TikTok: hay {len(nuevos)} post(s) atrasados; el siguiente saldrá cuando pasen 6 h desde el último.")
        nuevos = []
    nuevos = nuevos[:1]
    if simular:
        for post in procesando + nuevos:
            texto = texto_tiktok(post)
            resumen(f"[simulación TikTok · {modo()}] {post['fecha']} · {post.get('tipo')} · {post['id']}")
            if post.get("tipo") == "reel":
                print("    vídeo:", post["video"])
            else:
                for r in post["imagenes"]:
                    print("    foto:", url_fotos(r) if os.environ.get("TIKTOK_MEDIA_BASE_URL") or os.environ.get("GITHUB_REPOSITORY") else r)
            print("    texto:", texto.replace("\n", " ⏎ ")[:300])
        return 0
    if not os.environ.get("TIKTOK_REFRESH_TOKEN", "").strip():
        resumen(f"TikTok: esperando a que se conecte la cuenta. Hay {len(listos)} post(s) listos.")
        return 0
    token = token_de_acceso()
    zona = ZoneInfo(cola.get("zona", "Europe/Madrid"))
    fallos = 0
    for post in procesando + nuevos:
        tk = post.setdefault("tiktok", {})
        try:
            if tk.get("estado") != "procesando":
                tk["publish_id"] = publicar_en_tiktok(token, post)
                tk["modo"] = modo()
                tk["enviado_en"] = datetime.now(zona).isoformat(timespec="minutes")
                tk["estado"] = "procesando"
                guardar_cola(cola)
            final = estado_envio(token, tk["publish_id"])
            if final == "PROCESANDO":
                resumen(f"TikTok: {post['id']} sigue procesándose; se mira en la próxima ejecución.")
            else:
                tk["estado"] = "publicado" if final == "PUBLISH_COMPLETE" else "en_bandeja"
                tk.pop("error", None)
                aviso = "publicado" if final == "PUBLISH_COMPLETE" else "en la bandeja de TikTok: ábrelo en el móvil y pulsa Publicar"
                resumen(f"TikTok: {post['id']} {aviso}.")
        except ErrorTikTok as e:
            fallos += 1
            tk["intentos"] = tk.get("intentos", 0) + 1
            tk["error"] = str(e)
            tk["estado"] = "error" if tk["intentos"] >= MAX_INTENTOS else "pendiente"
            resumen(f"TikTok: ERROR en {post['id']} (intento {tk['intentos']}): {e}")
        except (KeyError, OSError) as e:
            fallos += 1
            tk["intentos"] = tk.get("intentos", 0) + 1
            tk["error"] = f"{type(e).__name__}: {e}"
            tk["estado"] = "error" if tk["intentos"] >= MAX_INTENTOS else "pendiente"
            resumen(f"TikTok: ERROR en {post['id']} (intento {tk['intentos']}): {tk['error']}")
        guardar_cola(cola)
    return 1 if fallos else 0


def modo_comprobar():
    if not os.environ.get("TIKTOK_REFRESH_TOKEN", "").strip():
        resumen("TikTok: todavía sin conectar (CONFIGURAR_TIKTOK.md).")
        return 0
    token = token_de_acceso()
    datos = api(token, "post/publish/creator_info/query/")
    resumen(f"TikTok conectado: @{datos.get('creator_username')} ({datos.get('creator_nickname')}).")
    resumen(f"Privacidades que deja TikTok ahora: {', '.join(datos.get('privacy_level_options', []))}.")
    resumen(f"Modo de publicación: {modo()}.")
    cola = cargar_cola()
    pend = [p for p in cola["posts"] if va_a_tiktok(p, cola)
            and p.get("tiktok", {}).get("estado", "pendiente") == "pendiente"]
    resumen(f"En la cola de TikTok: {len(pend)} pendientes. Próximo: {min((p['fecha'] for p in pend), default='ninguno')}.")
    return 0


def modo_conectar():
    codigo = os.environ.get("TIKTOK_CODIGO", "").strip()
    if not codigo:
        raise ErrorTikTok("Falta el código de TikTok (pégalo al lanzar «Conectar TikTok»).")
    codigo = urllib.parse.unquote(codigo)
    repo = os.environ.get("GITHUB_REPOSITORY", "")
    redireccion = os.environ.get("TIKTOK_REDIRECT_URI", "").strip()
    if not redireccion and "/" in repo:
        dueno, nombre = repo.split("/", 1)
        redireccion = f"https://{dueno.lower()}.github.io/{nombre}/tiktok/"
    r = pedir_token(grant_type="authorization_code", code=codigo, redirect_uri=redireccion)
    _guardar_clave(r["refresh_token"])
    dias = int(r.get("refresh_expires_in", 0)) // 86400
    resumen(f"Cuenta de TikTok conectada. Permisos: {r.get('scope')}. La clave vale {dias} días y se renueva sola.")
    return 0


if __name__ == "__main__":
    args = set(sys.argv[1:])
    try:
        if "--comprobar" in args:
            sys.exit(modo_comprobar())
        if "--conectar" in args:
            sys.exit(modo_conectar())
        sys.exit(modo_publicar(simular="--simular" in args))
    except ErrorTikTok as e:
        resumen(f"TikTok: ERROR: {e}")
        sys.exit(1)
