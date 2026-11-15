#!/usr/bin/env python3
"""Publicador automático de BomberoFlash para Instagram.

Lee cola.json y publica en Instagram los posts cuya fecha ya ha llegado, usando la
API oficial de Instagram (Instagram API with Instagram Login). Solo usa la librería
estándar de Python, así que no hace falta instalar nada.

Modos:
  python publicador/publicar.py              publica lo que toque (por defecto)
  python publicador/publicar.py --simular    enseña lo que publicaría, sin tocar Instagram
  python publicador/publicar.py --comprobar  comprueba el token y el cupo diario
  python publicador/publicar.py --renovar    renueva el token y lo deja en el fichero TOKEN_OUT

Tipos de entrada en cola.json ("tipo"):
  imagen / carrusel  "imagenes": 1 a 10 JPG y "texto"
  historia           "imagenes": [un JPG] o "video": "media/....mp4" (sin texto: Instagram no lo admite)
  reel               "video": "media/....mp4" y "texto"; "solo_reels": true para no sacarlo en el feed

Variables de entorno:
  IG_ACCESS_TOKEN    token de larga duración de la cuenta de Instagram (obligatorio salvo al simular)
  IG_USER_ID         id de la cuenta de Instagram (si falta, se consulta)
  MEDIA_BASE_URL     URL pública de la carpeta del repositorio donde están las imágenes
                     (por defecto, raw.githubusercontent.com de este repositorio)
  IG_API_VERSION     versión de la API (por defecto v23.0)
  MAX_POR_EJECUCION  posts como máximo por ejecución (por defecto 1)
  TOKEN_OUT          fichero donde --renovar escribe el token nuevo
"""
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from zoneinfo import ZoneInfo

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COLA = os.path.join(RAIZ, "cola.json")
VERSION = os.environ.get("IG_API_VERSION", "v23.0")


def es_token_facebook():
    """Los tokens del inicio de sesión unificado/Facebook empiezan por EAA y van por graph.facebook.com."""
    return os.environ.get("IG_ACCESS_TOKEN", "").strip().startswith("EAA")


def api():
    host = "graph.facebook.com" if es_token_facebook() else "graph.instagram.com"
    return f"https://{host}/{VERSION}"
MAX_INTENTOS = 3


class ErrorInstagram(Exception):
    pass


def llamar(metodo, ruta, **params):
    """Llama a la API de Instagram y devuelve el JSON de la respuesta."""
    token = os.environ.get("IG_ACCESS_TOKEN", "").strip()
    if not token:
        raise ErrorInstagram("Falta IG_ACCESS_TOKEN (el secreto de GitHub con el token de Instagram).")
    params["access_token"] = token
    datos = urllib.parse.urlencode(params).encode()
    url = ruta if ruta.startswith("http") else f"{api()}/{ruta}"
    if metodo == "GET":
        peticion = urllib.request.Request(f"{url}?{datos.decode()}")
    else:
        peticion = urllib.request.Request(url, data=datos, method="POST")
    try:
        with urllib.request.urlopen(peticion, timeout=60) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        cuerpo = e.read().decode(errors="replace")
        try:
            detalle = json.loads(cuerpo).get("error", {}).get("message", cuerpo)
        except ValueError:
            detalle = cuerpo
        raise ErrorInstagram(f"Instagram respondió {e.code}: {detalle}") from None


def id_cuenta():
    uid = os.environ.get("IG_USER_ID", "").strip()
    if uid:
        return uid
    if es_token_facebook():
        raise ErrorInstagram("Con este tipo de token hace falta el secreto IG_USER_ID (el ID de Instagram).")
    return str(llamar("GET", "me", fields="user_id")["user_id"])


def esperar_contenedor(contenedor, maximo=120):
    """Espera a que Instagram termine de procesar la imagen o el carrusel."""
    inicio = time.time()
    while True:
        estado = llamar("GET", contenedor, fields="status_code").get("status_code")
        if estado == "FINISHED":
            return
        if estado in ("ERROR", "EXPIRED"):
            raise ErrorInstagram(f"Instagram no pudo procesar el contenido ({estado}).")
        if time.time() - inicio > maximo:
            raise ErrorInstagram("Instagram tardó demasiado en procesar el contenido.")
        time.sleep(4)


def url_publica(ruta):
    base = os.environ.get("MEDIA_BASE_URL", "").strip()
    if not base:
        repo = os.environ.get("GITHUB_REPOSITORY")
        rama = os.environ.get("GITHUB_REF_NAME", "main")
        if not repo:
            raise ErrorInstagram("Falta MEDIA_BASE_URL (la dirección pública de las imágenes).")
        base = f"https://raw.githubusercontent.com/{repo}/{rama}/"
    return base.rstrip("/") + "/" + urllib.parse.quote(ruta.lstrip("/"))


def es_video(ruta):
    return ruta.lower().rsplit(".", 1)[-1] in ("mp4", "mov")


def contenedor_simple(uid, url, **extra):
    """Crea el contenedor de una imagen o un vídeo sueltos (post, historia o reel)."""
    if es_video(url):
        return llamar("POST", f"{uid}/media", video_url=url, **extra)["id"]
    return llamar("POST", f"{uid}/media", image_url=url, **extra)["id"]


def publicar_post(post, uid):
    tipo = post.get("tipo", "imagen")
    if tipo == "reel":
        video = url_publica(post["video"])
        contenedor = llamar("POST", f"{uid}/media", media_type="REELS", video_url=video,
                            caption=post.get("texto", ""),
                            share_to_feed="false" if post.get("solo_reels") else "true")["id"]
        esperar_contenedor(contenedor, maximo=600)
    elif tipo == "historia":
        # Una historia no lleva texto: lo que se quiera decir va dentro de la imagen o el vídeo.
        ruta = post.get("video") or post["imagenes"][0]
        contenedor = contenedor_simple(uid, url_publica(ruta), media_type="STORIES")
        esperar_contenedor(contenedor, maximo=600 if es_video(ruta) else 120)
    else:
        imagenes = [url_publica(r) for r in post["imagenes"]]
        if not 1 <= len(imagenes) <= 10:
            raise ErrorInstagram("Un post necesita entre 1 y 10 imágenes.")
        if len(imagenes) == 1:
            contenedor = llamar("POST", f"{uid}/media", image_url=imagenes[0], caption=post["texto"])["id"]
        else:
            hijos = []
            for url in imagenes:
                hijo = llamar("POST", f"{uid}/media", image_url=url, is_carousel_item="true")["id"]
                esperar_contenedor(hijo)
                hijos.append(hijo)
            contenedor = llamar("POST", f"{uid}/media", media_type="CAROUSEL",
                                children=",".join(hijos), caption=post["texto"])["id"]
        esperar_contenedor(contenedor)
    esperar_contenedor(contenedor)
    media_id = llamar("POST", f"{uid}/media_publish", creation_id=contenedor)["id"]
    try:
        enlace = llamar("GET", media_id, fields="permalink").get("permalink", "")
    except ErrorInstagram:
        enlace = ""
    return media_id, enlace


def cargar_cola():
    with open(COLA, encoding="utf-8") as f:
        return json.load(f)


def guardar_cola(cola):
    with open(COLA, "w", encoding="utf-8") as f:
        json.dump(cola, f, ensure_ascii=False, indent=2)
        f.write("\n")


def pendientes_para_ahora(cola):
    zona = ZoneInfo(cola.get("zona", "Europe/Madrid"))
    ahora = datetime.now(zona)
    listos = []
    for post in cola["posts"]:
        if post.get("estado", "pendiente") != "pendiente":
            continue
        if "redes" in post and "instagram" not in post["redes"]:
            continue  # solo para TikTok (publicador/tiktok.py)
        fecha = datetime.strptime(post["fecha"], "%Y-%m-%d %H:%M").replace(tzinfo=zona)
        if fecha <= ahora:
            listos.append((fecha, post))
    listos.sort(key=lambda p: p[0])
    return [p for _, p in listos]


def resumen(texto):
    ruta = os.environ.get("GITHUB_STEP_SUMMARY")
    print(texto)
    if ruta:
        with open(ruta, "a", encoding="utf-8") as f:
            f.write(texto + "\n")


def hay_atraso_reciente(cola, listos):
    """Si el primer post lleva más de 2 h de retraso (el publicador estuvo parado),
    no publica si ya salió otro en las últimas 20 h: así los atrasados salen de uno en uno al día."""
    zona = ZoneInfo(cola.get("zona", "Europe/Madrid"))
    ahora = datetime.now(zona)
    primero = datetime.strptime(listos[0]["fecha"], "%Y-%m-%d %H:%M").replace(tzinfo=zona)
    if (ahora - primero).total_seconds() < 2 * 3600:
        return False
    fechas = [datetime.fromisoformat(p["publicado_en"]) for p in cola["posts"]
              if p.get("publicado_en") and p.get("tipo") != "historia"]
    return bool(fechas) and (ahora - max(fechas)).total_seconds() < 20 * 3600


def modo_publicar(simular=False):
    cola = cargar_cola()
    listos = pendientes_para_ahora(cola)
    maximo = int(os.environ.get("MAX_POR_EJECUCION", "1"))
    if not listos:
        resumen("No hay nada que publicar ahora.")
        return 0
    # Las historias van aparte: salen todas las que toquen, en orden, y no cuentan para el límite.
    historias = [p for p in listos if p.get("tipo") == "historia"]
    feed = [p for p in listos if p.get("tipo") != "historia"]
    if feed and hay_atraso_reciente(cola, feed):
        resumen(f"Hay {len(feed)} post(s) atrasados; el siguiente saldrá cuando pasen 20 h desde el último.")
        feed = []
    listos = historias + feed[:maximo]
    if not listos:
        return 0
    if not simular and not os.environ.get("IG_ACCESS_TOKEN", "").strip():
        # Aún sin conectar Instagram (CONFIGURAR.md): esperar sin dar error cada hora.
        resumen(f"Esperando el token de Instagram. Hay {len(listos)} post(s) listos; saldrán cuando esté configurado.")
        return 0
    uid = None if simular else id_cuenta()
    fallos = 0
    for post in listos:
        if simular:
            archivos = [post["video"]] if post.get("video") else post.get("imagenes", [])
            resumen(f"[simulación] {post['fecha']} · {post.get('tipo', 'imagen')} · {post['id']} · {len(archivos)} archivo(s)")
            for r in archivos:
                print("   ", url_publica(r) if os.environ.get("MEDIA_BASE_URL") or os.environ.get("GITHUB_REPOSITORY") else r)
            continue
        try:
            media_id, enlace = publicar_post(post, uid)
            post.update(estado="publicado", instagram_id=media_id, enlace=enlace,
                        publicado_en=datetime.now(ZoneInfo(cola.get("zona", "Europe/Madrid"))).isoformat(timespec="minutes"))
            post.pop("error", None)
            resumen(f"Publicado {post['id']} · {enlace or media_id}")
        except ErrorInstagram as e:
            fallos += 1
            post["intentos"] = post.get("intentos", 0) + 1
            post["error"] = str(e)
            if post["intentos"] >= MAX_INTENTOS:
                post["estado"] = "error"
            resumen(f"ERROR en {post['id']} (intento {post['intentos']}): {e}")
        guardar_cola(cola)
    return 1 if fallos else 0


def modo_comprobar():
    uid = os.environ.get("IG_USER_ID", "").strip()
    if es_token_facebook():
        if not uid:
            raise ErrorInstagram("Con este tipo de token hace falta el secreto IG_USER_ID (el ID de Instagram).")
        yo = llamar("GET", uid, fields="username")
        yo["user_id"] = uid
    else:
        yo = llamar("GET", "me", fields="user_id,username")
        uid = uid or yo["user_id"]
    cupo = llamar("GET", f"{uid}/content_publishing_limit", fields="quota_usage,config")
    usado = cupo.get("data", [{}])[0]
    resumen(f"Token válido para @{yo.get('username')} (id {yo.get('user_id')}).")
    resumen(f"Publicaciones por API en las últimas 24 h: {usado.get('quota_usage', '?')} "
            f"de {usado.get('config', {}).get('quota_total', '?')}.")
    cola = cargar_cola()
    pend = [p for p in cola["posts"] if p.get("estado", "pendiente") == "pendiente"]
    resumen(f"En la cola: {len(pend)} pendientes. Próximo: {min((p['fecha'] for p in pend), default='ninguno')}.")
    return 0


def modo_renovar():
    if not os.environ.get("IG_ACCESS_TOKEN", "").strip():
        resumen("Todavía no hay token de Instagram: nada que renovar.")
        return 0
    if es_token_facebook():
        resumen("El token es de usuario del sistema o de Facebook: no caduca o no se renueva así. Nada que hacer.")
        return 0
    r = llamar("GET", "https://graph.instagram.com/refresh_access_token", grant_type="ig_refresh_token")
    nuevo = r["access_token"]
    dias = int(r.get("expires_in", 0)) // 86400
    salida = os.environ.get("TOKEN_OUT")
    if salida:
        with open(salida, "w", encoding="utf-8") as f:
            f.write(nuevo)
    resumen(f"Token renovado: vale {dias} días más.")
    return 0


if __name__ == "__main__":
    args = set(sys.argv[1:])
    try:
        if "--comprobar" in args:
            sys.exit(modo_comprobar())
        if "--renovar" in args:
            sys.exit(modo_renovar())
        sys.exit(modo_publicar(simular="--simular" in args))
    except ErrorInstagram as e:
        resumen(f"ERROR: {e}")
        sys.exit(1)
