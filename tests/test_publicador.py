"""Tests del publicador local: portada, ID3, índice JSON y feed.xml."""

import xml.etree.ElementTree as ET
from datetime import UTC, date, datetime
from email.utils import parsedate_to_datetime
from pathlib import Path

import pytest

from noticia.config import settings
from noticia.publicador import (
    EpisodioPublicable,
    NoticiaCitada,
    asegurar_portada,
    cargar_indice,
    construir_notas,
    episodio_publicado,
    escribir_atomico,
    etiquetar_mp3,
    guid_podcast,
    publicar_episodio,
    registrar_episodio,
    titulo_episodio,
)

NS = {
    "itunes": "http://www.itunes.com/dtds/podcast-1.0.dtd",
    "podcast": "https://podcastindex.org/namespace/1.0",
}


@pytest.fixture
def mp3_de_prueba(tmp_path) -> Path:
    pytest.importorskip("pydub")
    from pydub.generators import Sine

    ruta = tmp_path / "fuente.mp3"
    tono = Sine(440).to_audio_segment(duration=2000).apply_gain(-20)
    tono.export(ruta, format="mp3")
    return ruta


def test_titulo_episodio():
    assert titulo_episodio(date(2026, 9, 24)) == "NoticIA · jueves 24 de septiembre de 2026"


def test_guid_podcast_vector_oficial():
    # Vector oficial de la especificación Podcast Namespace
    # (Podcastindex-org/podcast-namespace, docs/tags/guid.md):
    # mp3s.nashownotes.com/pc20rss.xml -> 917393e3-1b1e-5cef-ace4-edaa54e1f810
    assert (
        guid_podcast("https://mp3s.nashownotes.com/pc20rss.xml")
        == "917393e3-1b1e-5cef-ace4-edaa54e1f810"
    )


def test_guid_podcast_es_estable_sin_esquema_ni_barra_final():
    assert guid_podcast("https://podnews.net/rss") == guid_podcast("podnews.net/rss/")


def test_construir_notas_escapa_html():
    noticias = [
        NoticiaCitada(
            bloque="espana", titular="<Ataque> & engaño", fuente="El País", url="https://x.test"
        ),
    ]
    texto, html_ = construir_notas(noticias, date(2026, 9, 24))
    assert "<Ataque> & engaño" in texto
    assert "&lt;Ataque&gt;" in html_
    assert "&amp;" in html_
    assert "<Ataque>" not in html_


def test_construir_notas_agrupa_por_bloque():
    noticias = [
        NoticiaCitada(bloque="espana", titular="Uno", fuente="A", url="https://a.test"),
        NoticiaCitada(bloque="futbol", titular="Dos", fuente="B", url="https://b.test"),
    ]
    texto, html_ = construir_notas(noticias, date(2026, 9, 24))
    assert "España" in texto
    assert "Fútbol" in texto
    assert "Voces sintéticas generadas con IA." in texto
    assert "Voces sintéticas generadas con IA." in html_


def test_asegurar_portada_medidas_formato_y_peso(tmp_path):
    from PIL import Image

    ruta = tmp_path / "portada.jpg"
    resultado = asegurar_portada(ruta)
    assert resultado == ruta
    with Image.open(resultado) as img:
        assert img.size == (3000, 3000)
        assert img.mode == "RGB"
    assert resultado.stat().st_size < 500_000


def test_asegurar_portada_no_se_regenera(tmp_path):
    ruta = tmp_path / "portada.jpg"
    asegurar_portada(ruta)
    mtime_antes = ruta.stat().st_mtime_ns
    asegurar_portada(ruta)
    assert ruta.stat().st_mtime_ns == mtime_antes


def test_etiquetar_mp3_escribe_tit2_y_apic(tmp_path, mp3_de_prueba):
    from mutagen.id3 import ID3

    portada = asegurar_portada(tmp_path / "portada.jpg")
    etiquetar_mp3(mp3_de_prueba, "Mi episodio", date(2026, 9, 24), "Descripción de prueba", portada)

    tags = ID3(mp3_de_prueba)
    assert str(tags["TIT2"]) == "Mi episodio"
    assert tags.getall("APIC")
    assert tags.getall("APIC")[0].mime == "image/jpeg"


def test_escribir_atomico_texto_y_bytes(tmp_path):
    ruta_txt = tmp_path / "sub" / "fichero.txt"
    escribir_atomico(ruta_txt, "hola")
    assert ruta_txt.read_text(encoding="utf-8") == "hola"
    assert not ruta_txt.with_suffix(ruta_txt.suffix + ".tmp").exists()

    ruta_bin = tmp_path / "fichero.bin"
    escribir_atomico(ruta_bin, b"\x00\x01")
    assert ruta_bin.read_bytes() == b"\x00\x01"


def test_cargar_indice_inexistente(tmp_path):
    assert cargar_indice(tmp_path / "no-existe.json") == {"version": 1, "episodios": []}


def test_cargar_indice_corrupto_no_rompe(tmp_path):
    ruta = tmp_path / "episodios.json"
    ruta.write_text("no es json", encoding="utf-8")
    assert cargar_indice(ruta) == {"version": 1, "episodios": []}


def test_registrar_episodio_conserva_guid_y_publicado():
    indice = {
        "version": 1,
        "episodios": [
            {
                "id": "2026-09-24",
                "guid": "g1",
                "publicado": "2026-09-24T08:00:00+02:00",
                "titulo": "viejo",
            },
        ],
    }
    nuevo = registrar_episodio(
        indice,
        {
            "id": "2026-09-24",
            "guid": "g2",
            "publicado": "2026-09-25T08:00:00+02:00",
            "titulo": "nuevo",
        },
    )
    assert len(nuevo["episodios"]) == 1
    entrada = nuevo["episodios"][0]
    assert entrada["guid"] == "g1"
    assert entrada["publicado"] == "2026-09-24T08:00:00+02:00"
    assert entrada["titulo"] == "nuevo"


def test_registrar_episodio_ordena_por_id_descendente():
    indice = {"version": 1, "episodios": [{"id": "2026-09-20", "guid": "g0", "publicado": "x"}]}
    nuevo = registrar_episodio(indice, {"id": "2026-09-24", "guid": "g1", "publicado": "y"})
    assert [e["id"] for e in nuevo["episodios"]] == ["2026-09-24", "2026-09-20"]


def _episodio_publicable(mp3: Path, fecha: date = date(2026, 9, 24)) -> EpisodioPublicable:
    return EpisodioPublicable(
        fecha=fecha,
        mp3=mp3,
        noticias=[
            NoticiaCitada(
                bloque="espana", titular="Titular uno", fuente="Fuente A", url="https://a.test"
            ),
            NoticiaCitada(
                bloque="futbol", titular="Titular dos", fuente="Fuente B", url="https://b.test"
            ),
        ],
        capitulos=[("intro", 0.0), ("espana", 5.0)],
        motor_voz="edge",
    )


def test_publicar_episodio_es_idempotente(tmp_path, mp3_de_prueba, monkeypatch):
    monkeypatch.setattr(settings, "publicacion_url_base", "http://localhost:8000")
    carpeta = tmp_path / "publicacion"
    ep = _episodio_publicable(mp3_de_prueba)

    ahora = datetime(2026, 9, 24, 8, 0, 0, tzinfo=UTC)
    ruta_feed_1 = publicar_episodio(ep, carpeta=carpeta, ahora=ahora)
    indice_1 = cargar_indice(carpeta / "episodios.json")

    ahora_2 = datetime(2026, 9, 24, 20, 0, 0, tzinfo=UTC)
    ruta_feed_2 = publicar_episodio(ep, carpeta=carpeta, ahora=ahora_2)
    indice_2 = cargar_indice(carpeta / "episodios.json")

    assert ruta_feed_1 == ruta_feed_2 == carpeta / "feed.xml"
    assert len(indice_2["episodios"]) == 1
    assert indice_1["episodios"][0]["guid"] == indice_2["episodios"][0]["guid"]
    assert indice_1["episodios"][0]["publicado"] == indice_2["episodios"][0]["publicado"]


def test_publicar_episodio_enclosure_length_coincide_con_fichero(
    tmp_path, mp3_de_prueba, monkeypatch
):
    monkeypatch.setattr(settings, "publicacion_url_base", "http://localhost:8000")
    carpeta = tmp_path / "publicacion"
    ep = _episodio_publicable(mp3_de_prueba)

    ruta_feed = publicar_episodio(ep, carpeta=carpeta)
    feed = ruta_feed.read_text(encoding="utf-8")
    raiz = ET.fromstring(feed)
    item = raiz.find("channel/item")
    enclosure = item.find("enclosure")
    mp3_publicado = carpeta / "episodios" / "2026-09-24.mp3"

    assert int(enclosure.attrib["length"]) == mp3_publicado.stat().st_size
    assert enclosure.attrib["url"].startswith("http://localhost:8000/")


def test_generar_feed_valido_y_completo(tmp_path, mp3_de_prueba, monkeypatch):
    monkeypatch.setattr(settings, "publicacion_url_base", "http://localhost:8000")
    carpeta = tmp_path / "publicacion"
    ep = _episodio_publicable(mp3_de_prueba)
    ruta_feed = publicar_episodio(ep, carpeta=carpeta)

    feed = ruta_feed.read_text(encoding="utf-8")
    raiz = ET.fromstring(feed)
    canal = raiz.find("channel")
    item = canal.find("item")

    assert item.find("title") is not None
    assert item.find("enclosure") is not None
    assert item.find("guid") is not None
    assert canal.find("itunes:image", NS) is not None
    assert canal.find("itunes:category", NS) is not None
    assert canal.find("language").text == "es-ES"

    pub_date = item.find("pubDate").text
    assert parsedate_to_datetime(pub_date) is not None


def test_generar_feed_sin_email_no_hay_owner(tmp_path, mp3_de_prueba, monkeypatch):
    monkeypatch.setattr(settings, "publicacion_url_base", "http://localhost:8000")
    monkeypatch.setattr(settings, "podcast_email", "")
    carpeta = tmp_path / "publicacion"
    ep = _episodio_publicable(mp3_de_prueba)
    ruta_feed = publicar_episodio(ep, carpeta=carpeta)

    raiz = ET.fromstring(ruta_feed.read_text(encoding="utf-8"))
    canal = raiz.find("channel")
    assert canal.find("itunes:owner", NS) is None
    assert canal.find("podcast:locked", NS) is None


def test_generar_feed_con_email_incluye_owner(tmp_path, mp3_de_prueba, monkeypatch):
    monkeypatch.setattr(settings, "publicacion_url_base", "http://localhost:8000")
    monkeypatch.setattr(settings, "podcast_email", "hola@noticia.test")
    carpeta = tmp_path / "publicacion"
    ep = _episodio_publicable(mp3_de_prueba)
    ruta_feed = publicar_episodio(ep, carpeta=carpeta)

    raiz = ET.fromstring(ruta_feed.read_text(encoding="utf-8"))
    canal = raiz.find("channel")
    assert canal.find("itunes:owner", NS) is not None
    assert canal.find("podcast:locked", NS) is not None


def test_generar_feed_incluye_capitulos_y_transcripcion(tmp_path, mp3_de_prueba, monkeypatch):
    monkeypatch.setattr(settings, "publicacion_url_base", "http://localhost:8000")
    carpeta = tmp_path / "publicacion"
    guion = tmp_path / "guion.md"
    guion.write_text("Álex: hola\n", encoding="utf-8")
    ep = EpisodioPublicable(
        fecha=date(2026, 9, 24),
        mp3=mp3_de_prueba,
        noticias=[],
        capitulos=[("intro", 0.0)],
        guion=guion,
    )
    ruta_feed = publicar_episodio(ep, carpeta=carpeta)

    raiz = ET.fromstring(ruta_feed.read_text(encoding="utf-8"))
    item = raiz.find("channel/item")
    assert item.find("podcast:chapters", NS) is not None
    assert item.find("podcast:transcript", NS) is not None
    assert (carpeta / "episodios" / "2026-09-24.chapters.json").exists()
    assert (carpeta / "episodios" / "2026-09-24.txt").exists()


def test_episodio_publicado_pasa_de_false_a_true(tmp_path, mp3_de_prueba, monkeypatch):
    monkeypatch.setattr(settings, "publicacion_url_base", "http://localhost:8000")
    carpeta = tmp_path / "publicacion"
    fecha = date(2026, 9, 24)

    assert episodio_publicado(fecha, carpeta=carpeta) is False
    publicar_episodio(_episodio_publicable(mp3_de_prueba, fecha), carpeta=carpeta)
    assert episodio_publicado(fecha, carpeta=carpeta) is True
