"""Reloj del publicador.

GitHub retrasa o se salta muchas ejecuciones programadas («schedule») de este
repositorio: el 16/11/2026 pasó de las 09:06 a las 11:38 UTC sin ninguna. Este
reloj corre dentro de una ejecución normal de GitHub Actions (hasta 5 h 30 min),
mira la cola cada 2 minutos y lanza el flujo «Publicar» en cuanto llega la hora
de un post. Al terminar, el flujo reloj.yml se vuelve a lanzar a sí mismo.

Lanza «Publicar» cuando:
- llega la hora de un post (de Instagram o solo de TikTok), o
- hay un post de Instagram «pendiente» con la hora pasada (últimas 24 h) y han
  pasado 25 minutos desde el último lanzamiento (p. ej. dos posts a la misma hora,
  porque cada ejecución publica uno).

No publica nada por sí mismo ni usa claves de Instagram: solo lanza «Publicar».
"""
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

DURACION = int(os.environ.get("RELOJ_DURACION_SEG", str(5 * 3600 + 30 * 60)))
PAUSA = int(os.environ.get("RELOJ_PAUSA_SEG", "120"))
REINTENTO = timedelta(minutes=25)


def leer_cola():
    subprocess.run(["git", "fetch", "-q", "origin", "main"], check=False)
    salida = subprocess.run(["git", "show", "origin/main:cola.json"],
                            capture_output=True, text=True, check=True).stdout
    return json.loads(salida)


def fecha_de(post, zona):
    return datetime.strptime(post["fecha"], "%Y-%m-%d %H:%M").replace(tzinfo=zona)


def lanzar_publicar(motivo):
    print(f"{datetime.now().isoformat(timespec='seconds')} · lanzo «Publicar»: {motivo}", flush=True)
    r = subprocess.run(["gh", "workflow", "run", "publicar.yml", "--ref", "main", "-f", "modo=publicar"],
                       capture_output=True, text=True)
    if r.returncode != 0:
        print(f"::warning::No se pudo lanzar «Publicar»: {r.stderr.strip()}", flush=True)
        return False
    return True


def decidir(cola, desde, ahora, ultimo_lanzamiento):
    """Devuelve el motivo para lanzar «Publicar» o None."""
    zona = ZoneInfo(cola.get("zona", "Europe/Madrid"))
    llegan = []
    atrasados = []
    for post in cola["posts"]:
        if post.get("estado") == "archivado":
            continue
        try:
            f = fecha_de(post, zona)
        except (KeyError, ValueError):
            continue
        if desde < f <= ahora:
            llegan.append(post["id"])
        if post.get("estado") == "pendiente" and ahora - timedelta(hours=24) <= f <= ahora:
            atrasados.append(post["id"])
    if llegan:
        return "llega la hora de " + ", ".join(llegan)
    if atrasados and (ultimo_lanzamiento is None or ahora - ultimo_lanzamiento >= REINTENTO):
        return "siguen pendientes " + ", ".join(atrasados)
    return None


def main():
    inicio = time.monotonic()
    zona = ZoneInfo(leer_cola().get("zona", "Europe/Madrid"))
    # Al arrancar se mira también lo que haya llegado en los últimos 20 minutos,
    # por si el reloj anterior terminó justo antes de una hora de publicación.
    desde = datetime.now(zona) - timedelta(minutes=20)
    ultimo = None
    while time.monotonic() - inicio < DURACION:
        try:
            cola = leer_cola()
            ahora = datetime.now(zona)
            motivo = decidir(cola, desde, ahora, ultimo)
            desde = ahora
            if motivo and lanzar_publicar(motivo):
                ultimo = ahora
        except Exception as e:  # un fallo puntual (red, JSON a medio subir) no para el reloj
            print(f"::warning::Fallo del reloj: {e}", flush=True)
        time.sleep(PAUSA)
    print("Fin del turno del reloj; reloj.yml lo vuelve a lanzar.", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
