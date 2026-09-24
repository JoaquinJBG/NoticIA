"""Publicación local del episodio: portada, etiquetas ID3, índice JSON y feed.xml.

Genera y mantiene, de forma idempotente, todo lo que necesita un feed de podcast
servido en local: `output/publicacion/feed.xml`, `episodios.json` (índice) y
`portada.jpg`, más el MP3, los capítulos y la transcripción de cada episodio.
"""

from __future__ import annotations

import html
import json
import logging
import os
import re
import shutil
import uuid
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import date, datetime
from email.utils import format_datetime
from pathlib import Path
from typing import Any

from noticia.bloques import NOMBRE_BLOQUE, ORDEN_BLOQUES
from noticia.config import settings
from noticia.fechas import ahora_madrid, formatear_fecha_larga

logger = logging.getLogger("noticia.publicador")

# Namespace fijo de la especificación Podcast Namespace para generar GUID
# estables a partir de una URL: https://podcastindex.org/namespace/1.0/tags/guid
_NAMESPACE_GUID_PODCAST = uuid.UUID("ead4c236-bf58-58c6-a2c6-a6b28d128cb6")

NS_ITUNES = "http://www.itunes.com/dtds/podcast-1.0.dtd"
NS_PODCAST = "https://podcastindex.org/namespace/1.0"
NS_ATOM = "http://www.w3.org/2005/Atom"
NS_CONTENT = "http://purl.org/rss/1.0/modules/content/"

_ANCHO_PORTADA = 3000
_ALTO_PORTADA = 3000
_TAMANO_MAX_PORTADA_BYTES = 500_000


@dataclass(frozen=True)
class NoticiaCitada:
    bloque: str
    titular: str
    fuente: str
    url: str


@dataclass(frozen=True)
class EpisodioPublicable:
    fecha: date
    mp3: Path
    noticias: list[NoticiaCitada]
    capitulos: list[tuple[str, float]]
    guion: Path | None = None
    motor_voz: str = ""


def titulo_episodio(fecha: date) -> str:
    return f"NoticIA · {formatear_fecha_larga(fecha)}"


def construir_notas(noticias: list[NoticiaCitada], fecha: date) -> tuple[str, str]:
    """Devuelve las notas del episodio en (texto plano, HTML)."""
    por_bloque: dict[str, list[NoticiaCitada]] = {}
    for noticia in noticias:
        por_bloque.setdefault(noticia.bloque, []).append(noticia)

    titulares = [n.titular for n in noticias[:5]]
    if titulares:
        resumen = "Hoy en NoticIA: " + "; ".join(titulares) + "."
    else:
        resumen = f"Episodio de NoticIA del {formatear_fecha_larga(fecha)}."

    lineas_texto = [resumen, "", "Noticias de hoy:"]
    lineas_html = [f"<p>{html.escape(resumen)}</p>", "<p><strong>Noticias de hoy</strong></p>"]

    for bloque in ORDEN_BLOQUES:
        items = por_bloque.get(bloque)
        if not items:
            continue
        nombre = NOMBRE_BLOQUE.get(bloque, bloque)
        lineas_texto.append(f"\n{nombre}:")
        html_items = []
        for noticia in items:
            lineas_texto.append(f"- {noticia.titular} — {noticia.fuente} ({noticia.url})")
            url_escapada = html.escape(noticia.url)
            html_items.append(
                f"<li>{html.escape(noticia.titular)} — {html.escape(noticia.fuente)} "
                f'(<a href="{url_escapada}">{url_escapada}</a>)</li>'
            )
        lineas_html.append(
            f"<p><strong>{html.escape(nombre)}</strong></p><ul>{''.join(html_items)}</ul>"
        )

    lineas_texto.append("\nVoces sintéticas generadas con IA.")
    lineas_html.append("<p>Voces sintéticas generadas con IA.</p>")

    return "\n".join(lineas_texto), "\n".join(lineas_html)


def _centrar_texto(
    dibujo: Any, texto: str, fuente: Any, ancho_lienzo: int, y: float, color: tuple[int, int, int]
) -> None:
    caja = dibujo.textbbox((0, 0), texto, font=fuente)
    ancho_texto = caja[2] - caja[0]
    x = (ancho_lienzo - ancho_texto) / 2 - caja[0]
    dibujo.text((x, y), texto, font=fuente, fill=color)


def asegurar_portada(ruta: Path) -> Path:
    """Genera una portada 3000x3000 si `ruta` no existe todavía. Idempotente."""
    if ruta.exists():
        return ruta

    from PIL import Image, ImageDraw, ImageFont  # import pesado, perezoso

    ruta.parent.mkdir(parents=True, exist_ok=True)

    imagen = Image.new("RGB", (_ANCHO_PORTADA, _ALTO_PORTADA), color=(16, 18, 28))
    dibujo = ImageDraw.Draw(imagen)
    fuente_titulo = ImageFont.load_default(size=260)
    fuente_subtitulo = ImageFont.load_default(size=90)
    _centrar_texto(
        dibujo,
        "NoticIA",
        fuente_titulo,
        _ANCHO_PORTADA,
        _ALTO_PORTADA / 2 - 160,
        (245, 245, 250),
    )
    _centrar_texto(
        dibujo,
        "Álex y María",
        fuente_subtitulo,
        _ANCHO_PORTADA,
        _ALTO_PORTADA / 2 + 140,
        (190, 195, 210),
    )

    calidad = 85
    while True:
        imagen.save(ruta, format="JPEG", quality=calidad, optimize=True, progressive=True)
        if ruta.stat().st_size <= _TAMANO_MAX_PORTADA_BYTES or calidad <= 35:
            break
        calidad -= 10

    logger.info("Portada generada en %s (%d bytes, calidad %d)", ruta, ruta.stat().st_size, calidad)
    return ruta


def etiquetar_mp3(ruta: Path, titulo: str, fecha: date, descripcion: str, portada: Path) -> None:
    """Escribe las etiquetas ID3 del episodio, incluida la portada como APIC."""
    from mutagen.id3 import APIC, COMM, ID3, TALB, TCON, TDRC, TIT2, TLAN, TPE1, ID3NoHeaderError

    try:
        etiquetas = ID3(ruta)
    except ID3NoHeaderError:
        etiquetas = ID3()

    etiquetas.setall("TIT2", [TIT2(encoding=3, text=titulo)])
    etiquetas.setall("TPE1", [TPE1(encoding=3, text="Álex y María")])
    etiquetas.setall("TALB", [TALB(encoding=3, text=settings.podcast_titulo)])
    etiquetas.setall("TDRC", [TDRC(encoding=3, text=fecha.isoformat())])
    etiquetas.setall("TCON", [TCON(encoding=3, text="Podcast")])
    etiquetas.setall("TLAN", [TLAN(encoding=3, text="spa")])
    etiquetas.setall("COMM", [COMM(encoding=3, lang="spa", desc="", text=descripcion)])
    datos_portada = portada.read_bytes()
    etiquetas.setall(
        "APIC",
        [APIC(encoding=3, mime="image/jpeg", type=3, desc="Portada", data=datos_portada)],
    )
    etiquetas.save(ruta, v2_version=3)


def escribir_atomico(ruta: Path, contenido: str | bytes) -> None:
    """Escribe `contenido` en un fichero temporal y lo renombra sobre `ruta`."""
    ruta.parent.mkdir(parents=True, exist_ok=True)
    tmp = ruta.with_name(ruta.name + ".tmp")
    if isinstance(contenido, bytes):
        tmp.write_bytes(contenido)
    else:
        tmp.write_text(contenido, encoding="utf-8")
    os.replace(tmp, ruta)


def cargar_indice(ruta: Path) -> dict:
    if not ruta.exists():
        return {"version": 1, "episodios": []}
    try:
        return json.loads(ruta.read_text(encoding="utf-8"))
    except Exception as exc:
        logger.error("Índice de publicación corrupto en %s: %s", ruta, exc)
        return {"version": 1, "episodios": []}


def registrar_episodio(indice: dict, entrada: dict) -> dict:
    """Upsert de `entrada` por `id`, conservando `guid` y `publicado` si ya existía."""
    episodios = list(indice.get("episodios", []))
    existente = next((e for e in episodios if e["id"] == entrada["id"]), None)
    if existente is not None:
        entrada = {
            **entrada,
            "guid": existente.get("guid", entrada.get("guid")),
            "publicado": existente.get("publicado", entrada.get("publicado")),
        }
        episodios = [entrada if e["id"] == entrada["id"] else e for e in episodios]
    else:
        episodios.append(entrada)
    episodios.sort(key=lambda e: e["id"], reverse=True)
    return {**indice, "episodios": episodios}


def guid_podcast(url_feed: str) -> str:
    """UUIDv5 estable a partir de una URL, sin esquema ni barra final (spec Podcast Namespace)."""
    sin_esquema = re.sub(r"^https?://", "", url_feed).rstrip("/")
    return str(uuid.uuid5(_NAMESPACE_GUID_PODCAST, sin_esquema))


def _formatear_duracion(segundos: float) -> str:
    total = int(round(segundos))
    horas, resto = divmod(total, 3600)
    minutos, segs = divmod(resto, 60)
    return f"{horas:02d}:{minutos:02d}:{segs:02d}"


def generar_feed(indice: dict) -> str:
    ET.register_namespace("itunes", NS_ITUNES)
    ET.register_namespace("podcast", NS_PODCAST)
    ET.register_namespace("atom", NS_ATOM)
    ET.register_namespace("content", NS_CONTENT)

    base = settings.publicacion_url_base.rstrip("/")
    url_feed = f"{base}/feed.xml"
    url_imagen = f"{base}/portada.jpg"

    rss = ET.Element("rss", {"version": "2.0"})
    canal = ET.SubElement(rss, "channel")

    ET.SubElement(canal, "title").text = settings.podcast_titulo
    ET.SubElement(canal, "link").text = base
    ET.SubElement(canal, "description").text = settings.podcast_descripcion
    ET.SubElement(canal, "language").text = settings.podcast_idioma
    ET.SubElement(
        canal,
        f"{{{NS_ATOM}}}link",
        {"href": url_feed, "rel": "self", "type": "application/rss+xml"},
    )
    ET.SubElement(canal, f"{{{NS_PODCAST}}}guid").text = guid_podcast(url_feed)
    ET.SubElement(canal, f"{{{NS_ITUNES}}}author").text = settings.podcast_autor
    ET.SubElement(canal, f"{{{NS_ITUNES}}}explicit").text = (
        "true" if settings.podcast_explicito else "false"
    )
    ET.SubElement(canal, f"{{{NS_ITUNES}}}image", {"href": url_imagen})
    categoria = ET.SubElement(canal, f"{{{NS_ITUNES}}}category", {"text": "News"})
    ET.SubElement(categoria, f"{{{NS_ITUNES}}}category", {"text": "Daily News"})

    if settings.podcast_email:
        propietario = ET.SubElement(canal, f"{{{NS_ITUNES}}}owner")
        ET.SubElement(propietario, f"{{{NS_ITUNES}}}name").text = settings.podcast_autor
        ET.SubElement(propietario, f"{{{NS_ITUNES}}}email").text = settings.podcast_email
        ET.SubElement(canal, f"{{{NS_PODCAST}}}locked").text = "yes"

    episodios = indice.get("episodios", [])[: settings.max_items_feed]
    for episodio in episodios:
        item = ET.SubElement(canal, "item")
        ET.SubElement(item, "title").text = episodio["titulo"]
        ET.SubElement(item, "guid", {"isPermaLink": "false"}).text = episodio["guid"]
        ET.SubElement(item, "pubDate").text = format_datetime(
            datetime.fromisoformat(episodio["publicado"])
        )
        ET.SubElement(item, "description").text = episodio.get("notas_texto", "")
        contenido = ET.SubElement(item, f"{{{NS_CONTENT}}}encoded")
        contenido.text = episodio.get("notas_html", "")
        url_mp3 = f"{base}/{episodio['ruta_mp3']}"
        ET.SubElement(
            item,
            "enclosure",
            {"url": url_mp3, "length": str(episodio["bytes"]), "type": "audio/mpeg"},
        )
        ET.SubElement(item, f"{{{NS_ITUNES}}}duration").text = _formatear_duracion(
            episodio["duracion_s"]
        )
        ET.SubElement(item, f"{{{NS_ITUNES}}}explicit").text = (
            "true" if settings.podcast_explicito else "false"
        )
        ET.SubElement(item, f"{{{NS_ITUNES}}}image", {"href": url_imagen})
        if episodio.get("ruta_capitulos"):
            ET.SubElement(
                item,
                f"{{{NS_PODCAST}}}chapters",
                {
                    "url": f"{base}/{episodio['ruta_capitulos']}",
                    "type": "application/json+chapters",
                },
            )
        if episodio.get("ruta_transcripcion"):
            ET.SubElement(
                item,
                f"{{{NS_PODCAST}}}transcript",
                {"url": f"{base}/{episodio['ruta_transcripcion']}", "type": "text/plain"},
            )

    ET.indent(rss, space="  ")
    return '<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(rss, encoding="unicode")


def episodio_publicado(fecha: date, carpeta: Path | None = None) -> bool:
    carpeta = carpeta or settings.carpeta_publicacion
    indice = cargar_indice(carpeta / "episodios.json")
    id_episodio = fecha.isoformat()
    return any(e["id"] == id_episodio for e in indice.get("episodios", []))


def publicar_episodio(
    ep: EpisodioPublicable, carpeta: Path | None = None, ahora: datetime | None = None
) -> Path:
    """Publica (o republica de forma idempotente) un episodio y regenera el feed.

    Devuelve la ruta de `feed.xml`.
    """
    carpeta = carpeta or settings.carpeta_publicacion
    carpeta_episodios = carpeta / "episodios"
    carpeta_episodios.mkdir(parents=True, exist_ok=True)

    portada = asegurar_portada(carpeta / "portada.jpg")

    id_episodio = ep.fecha.isoformat()
    destino_mp3 = carpeta_episodios / f"{id_episodio}.mp3"
    shutil.copyfile(ep.mp3, destino_mp3)

    titulo = titulo_episodio(ep.fecha)
    notas_texto, notas_html = construir_notas(ep.noticias, ep.fecha)
    etiquetar_mp3(destino_mp3, titulo, ep.fecha, notas_texto, portada)

    tamano_bytes = destino_mp3.stat().st_size

    from mutagen.mp3 import MP3

    duracion_s = MP3(destino_mp3).info.length

    ruta_capitulos: str | None = None
    if ep.capitulos:
        datos_capitulos = {
            "version": "1.2.0",
            "chapters": [
                {"startTime": inicio, "title": NOMBRE_BLOQUE.get(bloque, bloque)}
                for bloque, inicio in ep.capitulos
            ],
        }
        ruta_capitulos_fs = carpeta_episodios / f"{id_episodio}.chapters.json"
        contenido_capitulos = json.dumps(datos_capitulos, ensure_ascii=False, indent=2)
        escribir_atomico(ruta_capitulos_fs, contenido_capitulos)
        ruta_capitulos = f"episodios/{id_episodio}.chapters.json"

    ruta_transcripcion: str | None = None
    if ep.guion is not None and ep.guion.exists():
        ruta_txt_fs = carpeta_episodios / f"{id_episodio}.txt"
        escribir_atomico(ruta_txt_fs, ep.guion.read_text(encoding="utf-8"))
        ruta_transcripcion = f"episodios/{id_episodio}.txt"

    ruta_indice = carpeta / "episodios.json"
    indice = cargar_indice(ruta_indice)
    momento_publicacion = ahora or ahora_madrid()
    url_feed = f"{settings.publicacion_url_base.rstrip('/')}/feed.xml"

    entrada = {
        "id": id_episodio,
        "titulo": titulo,
        "guid": guid_podcast(f"{url_feed}/{id_episodio}"),
        "publicado": momento_publicacion.isoformat(),
        "ruta_mp3": f"episodios/{id_episodio}.mp3",
        "bytes": tamano_bytes,
        "duracion_s": duracion_s,
        "notas_texto": notas_texto,
        "notas_html": notas_html,
        "ruta_capitulos": ruta_capitulos,
        "ruta_transcripcion": ruta_transcripcion,
        "motor_voz": ep.motor_voz,
    }
    indice = registrar_episodio(indice, entrada)
    escribir_atomico(ruta_indice, json.dumps(indice, ensure_ascii=False, indent=2))

    feed_xml = generar_feed(indice)
    ruta_feed = carpeta / "feed.xml"
    escribir_atomico(ruta_feed, feed_xml)

    logger.info("Episodio %s publicado en %s", id_episodio, ruta_feed)
    return ruta_feed
