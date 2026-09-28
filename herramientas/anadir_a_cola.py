#!/usr/bin/env python3
"""Añade posts a cola.json a partir de un plan (herramienta local, no se usa en GitHub).

Uso:
  python herramientas/anadir_a_cola.py plan.json

plan.json es una lista de posts:
  [{"id": "c04-caudal-critico",
    "fecha": "2026-10-20 10:00",
    "imagenes": ["C:/ruta/c04_1de7.png", "..."],     # PNG o JPG, en orden
    "texto": "Pie de foto...",
    "ia": false,
    "pregunta_id": "bf-exam-..."}]                    # opcional

Convierte cada imagen a JPEG (Instagram solo acepta JPEG por API), la copia a media/
con un nombre sin espacios y añade la entrada a la cola. Si un id ya existe, lo salta.
"""
import json
import os
import sys

from PIL import Image

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COLA = os.path.join(RAIZ, "cola.json")
MEDIA = os.path.join(RAIZ, "media")


def main(ruta_plan):
    with open(ruta_plan, encoding="utf-8") as f:
        plan = json.load(f)
    with open(COLA, encoding="utf-8") as f:
        cola = json.load(f)
    existentes = {p["id"] for p in cola["posts"]}
    os.makedirs(MEDIA, exist_ok=True)
    nuevos = 0
    for post in plan:
        if post["id"] in existentes:
            print("Ya estaba en la cola:", post["id"])
            continue
        rutas = []
        for n, origen in enumerate(post["imagenes"], 1):
            nombre = f"{post['id']}-{n}.jpg"
            imagen = Image.open(origen).convert("RGB")
            ancho, alto = imagen.size
            if not 0.8 <= ancho / alto <= 1.91:
                raise SystemExit(f"{origen}: proporción {ancho}x{alto} fuera de lo que admite Instagram (4:5 a 1.91:1).")
            imagen.save(os.path.join(MEDIA, nombre), "JPEG", quality=90, optimize=True, progressive=True)
            rutas.append(f"media/{nombre}")
        entrada = {
            "id": post["id"],
            "fecha": post["fecha"],
            "tipo": "carrusel" if len(rutas) > 1 else "imagen",
            "imagenes": rutas,
            "texto": post["texto"],
            "ia": bool(post.get("ia", False)),
            "estado": "pendiente",
        }
        if post.get("pregunta_id"):
            entrada["pregunta_id"] = post["pregunta_id"]
        cola["posts"].append(entrada)
        nuevos += 1
    cola["posts"].sort(key=lambda p: p["fecha"])
    with open(COLA, "w", encoding="utf-8") as f:
        json.dump(cola, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(f"Añadidos {nuevos} posts. Total en la cola: {len(cola['posts'])}.")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    main(sys.argv[1])
