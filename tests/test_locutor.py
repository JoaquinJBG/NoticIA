import asyncio
from pathlib import Path

import pytest

from noticia import locutor
from noticia.voz.base import ErrorMotorVoz, MotorNoDisponible, Turno

# --- Parser: comportamiento heredado -----------------------------------


def test_parsear_linea_alex_y_maria():
    assert locutor._parsear_linea("Álex: hola") == ("alex", "hola")
    assert locutor._parsear_linea("María: qué tal") == ("maria", "qué tal")


def test_parsear_linea_sin_tildes():
    assert locutor._parsear_linea("Alex: hola") == ("alex", "hola")
    assert locutor._parsear_linea("Maria: hola") == ("maria", "hola")


def test_parsear_linea_mencion_de_otro_locutor_no_confunde():
    # El bug antiguo: buscaba "álex:" en CUALQUIER posición y se lo atribuía a Álex.
    linea = "María: y entonces Álex: dijo que no"
    assert locutor._parsear_linea(linea) == ("maria", "y entonces Álex: dijo que no")


def test_parsear_linea_dos_puntos_en_la_frase():
    # split(":", 1) corta por el dos puntos del prefijo, no por el de la hora.
    assert locutor._parsear_linea("Álex: quedamos a las 15:30") == (
        "alex",
        "quedamos a las 15:30",
    )


def test_parsear_linea_no_dialogo_devuelve_none():
    assert locutor._parsear_linea("IMPORTANTE: no inventes hechos") is None
    assert locutor._parsear_linea("una línea cualquiera") is None
    assert locutor._parsear_linea("Santi: ya no existe") is None
    assert locutor._parsear_linea("Álex:") is None  # sin texto
    assert locutor._parsear_linea("") is None


# --- Parser: acotaciones y markdown en el prefijo -----------------------


def test_parsear_linea_con_acotacion_entre_parentesis():
    assert locutor._parsear_linea("Álex (riendo): hola") == ("alex", "hola")


def test_parsear_linea_con_negrita_markdown():
    assert locutor._parsear_linea("**María**: hola") == ("maria", "hola")


# --- parsear_turnos ------------------------------------------------------


def test_parsear_turnos_linea_continuacion_se_une():
    texto = "Álex: buenos días\ny bienvenidos al programa"
    turnos, descartadas = locutor.parsear_turnos(texto, "intro")
    assert descartadas == 0
    assert len(turnos) == 1
    assert turnos[0].texto == "buenos días y bienvenidos al programa"
    assert turnos[0].locutor == "alex"
    assert turnos[0].bloque == "intro"
    assert turnos[0].indice == 0


def test_parsear_turnos_linea_tras_blanco_se_descarta():
    texto = "Álex: buenos días\n\notra cosa suelta"
    turnos, descartadas = locutor.parsear_turnos(texto, "intro")
    assert len(turnos) == 1
    assert turnos[0].texto == "buenos días"
    assert descartadas == 1


def test_parsear_turnos_forma_palabra_no_se_une_aunque_no_haya_blanco():
    texto = "Álex: buenos días\nSanti: esto no debería colarse"
    turnos, descartadas = locutor.parsear_turnos(texto, "intro")
    assert len(turnos) == 1
    assert turnos[0].texto == "buenos días"
    assert descartadas == 1


def test_parsear_turnos_indices_secuenciales_por_bloque():
    texto = "Álex: uno\nMaría: dos\nÁlex: tres"
    turnos, _ = locutor.parsear_turnos(texto, "espana")
    assert [t.indice for t in turnos] == [0, 1, 2]
    assert [t.locutor for t in turnos] == ["alex", "maria", "alex"]


def test_parsear_turnos_texto_vacio_tras_limpiar_se_descarta():
    texto = "Álex: (risas)"
    turnos, descartadas = locutor.parsear_turnos(texto, "friki")
    assert turnos == []
    assert descartadas == 1


# --- Motores falsos para probar la locución en paralelo -----------------


class _MotorFalso:
    """Motor de prueba: escribe el texto en el fichero, con retraso configurable."""

    def __init__(self, nombre="falso", extension="txt", concurrencia_maxima=6, fallar=None):
        self.nombre = nombre
        self.extension = extension
        self.concurrencia_maxima = concurrencia_maxima
        self._fallar = fallar or (lambda turno, intento: False)
        self.en_vuelo = 0
        self.maximo_en_vuelo = 0
        self.llamadas: list[tuple[str, str, str]] = []
        self._intentos: dict[tuple[str, int], int] = {}
        self.cargado = False

    def disponible(self):
        return True, ""

    async def cargar(self):
        self.cargado = True

    async def sintetizar(self, texto, locutor_id, ruta):
        self.en_vuelo += 1
        self.maximo_en_vuelo = max(self.maximo_en_vuelo, self.en_vuelo)
        try:
            await asyncio.sleep(0.01)
            clave = (texto, locutor_id)
            intento = self._intentos.get(clave, 0)
            self._intentos[clave] = intento + 1
            if self._fallar(texto, intento):
                raise ErrorMotorVoz(f"fallo simulado en intento {intento}")
            self.llamadas.append((texto, locutor_id, str(ruta)))
            Path(ruta).write_text(f"{locutor_id}:{texto}", encoding="utf-8")
            return Path(ruta)
        finally:
            self.en_vuelo -= 1

    async def cerrar(self):
        pass


class _MotorSiempreFalla(_MotorFalso):
    async def sintetizar(self, texto, locutor_id, ruta):
        raise ErrorMotorVoz("este motor siempre falla")


def test_locutar_episodio_conserva_el_orden(tmp_path):
    motor = _MotorFalso()
    bloques = {
        "espana": "Álex: uno\nMaría: dos",
        "futbol": "Álex: tres\nMaría: cuatro",
    }
    resultado = asyncio.run(locutor.locutar_episodio(bloques, [motor], tmp_path, concurrencia=6))
    assert [p.name for p in resultado.fragmentos_por_bloque["espana"]] == [
        "espana_0000.txt",
        "espana_0001.txt",
    ]
    assert [p.name for p in resultado.fragmentos_por_bloque["futbol"]] == [
        "futbol_0000.txt",
        "futbol_0001.txt",
    ]
    assert resultado.total_turnos == 4
    assert resultado.fallidos == []
    assert resultado.motores_usados["falso"] == 4


def test_locutar_episodio_respeta_la_concurrencia_maxima(tmp_path):
    motor = _MotorFalso(concurrencia_maxima=2)
    texto = "\n".join(f"Álex: turno {i}" for i in range(8))
    bloques = {"espana": texto}
    resultado = asyncio.run(locutor.locutar_episodio(bloques, [motor], tmp_path, concurrencia=2))
    assert resultado.total_turnos == 8
    assert motor.maximo_en_vuelo <= 2


def test_locutar_episodio_usa_el_motor_secundario_si_el_principal_falla_siempre(tmp_path):
    principal = _MotorSiempreFalla(nombre="principal")
    secundario = _MotorFalso(nombre="secundario")
    bloques = {"espana": "Álex: hola\nMaría: adiós"}
    resultado = asyncio.run(
        locutor.locutar_episodio(
            bloques, [principal, secundario], tmp_path, reintentos=0, espera_base_s=0
        )
    )
    assert resultado.fallidos == []
    assert resultado.motores_usados["secundario"] == 2
    assert "principal" not in resultado.motores_usados
    rutas = resultado.fragmentos_por_bloque["espana"]
    assert all(ruta.suffix == ".txt" for ruta in rutas)


def test_locutar_episodio_reintenta_antes_de_darse_por_vencido(tmp_path):
    fallos_restantes = {"n": 1}

    def _fallar_una_vez(texto, intento):
        if fallos_restantes["n"] > 0 and intento == 0:
            fallos_restantes["n"] -= 1
            return True
        return False

    motor = _MotorFalso(fallar=_fallar_una_vez)
    bloques = {"espana": "Álex: hola"}
    resultado = asyncio.run(
        locutor.locutar_episodio(bloques, [motor], tmp_path, reintentos=1, espera_base_s=0)
    )
    assert resultado.fallidos == []
    assert resultado.motores_usados["falso"] == 1


def test_locutar_episodio_lanza_error_si_superan_el_umbral_de_fallos(tmp_path, monkeypatch):
    monkeypatch.setattr(locutor.settings, "max_fraccion_fallos_locucion", 0.10)
    motor = _MotorSiempreFalla()
    bloques = {"espana": "Álex: uno\nMaría: dos\nÁlex: tres"}
    with pytest.raises(locutor.ErrorLocucion):
        asyncio.run(
            locutor.locutar_episodio(bloques, [motor], tmp_path, reintentos=0, espera_base_s=0)
        )


def test_locutar_episodio_arregla_el_bug_de_ficheros_sobrescritos(tmp_path):
    # Bug histórico: un contador global por episodio pisaba fragmentos de otros bloques.
    motor = _MotorFalso()
    bloques = {
        "espana": "Álex: contenido espana uno\nMaría: contenido espana dos",
        "friki": "Álex: contenido friki uno\nMaría: contenido friki dos",
    }
    resultado = asyncio.run(locutor.locutar_episodio(bloques, [motor], tmp_path))

    todas_las_rutas = [ruta for rutas in resultado.fragmentos_por_bloque.values() for ruta in rutas]
    assert len(todas_las_rutas) == len(set(todas_las_rutas)) == 4
    for ruta in todas_las_rutas:
        assert ruta.exists()
    contenido_espana = [
        ruta.read_text(encoding="utf-8") for ruta in resultado.fragmentos_por_bloque["espana"]
    ]
    assert contenido_espana == [
        "alex:contenido espana uno",
        "maria:contenido espana dos",
    ]
    contenido_friki = [
        ruta.read_text(encoding="utf-8") for ruta in resultado.fragmentos_por_bloque["friki"]
    ]
    assert contenido_friki == [
        "alex:contenido friki uno",
        "maria:contenido friki dos",
    ]


def test_locutar_episodio_necesita_al_menos_un_motor(tmp_path):
    with pytest.raises(ValueError):
        asyncio.run(locutor.locutar_episodio({"espana": "Álex: hola"}, [], tmp_path))


# --- procesar_guion_a_audio: compatibilidad con cli.py -------------------


def test_procesar_guion_a_audio_con_motor_inyectado_devuelve_rutas_str(tmp_path, monkeypatch):
    monkeypatch.setattr(locutor.settings, "carpeta_temp", str(tmp_path))
    motor = _MotorFalso()
    # La tercera línea, sin blanco de por medio y sin forma "Palabra:", se une
    # como continuación al turno de María (ver test_parsear_turnos_linea_continuacion_se_une).
    guion = "Álex: buenos días\nMaría: hola a todos\nsin prefijo de locutor"

    piezas = asyncio.run(locutor.procesar_guion_a_audio(guion, motores=[motor]))

    assert len(piezas) == 2
    assert all(isinstance(p, str) for p in piezas)
    assert Path(piezas[0]).read_text(encoding="utf-8") == "alex:buenos días"
    assert (
        Path(piezas[1]).read_text(encoding="utf-8") == "maria:hola a todos sin prefijo de locutor"
    )


def test_procesar_guion_a_audio_sin_motores_usa_motor_edge_por_defecto(tmp_path, monkeypatch):
    monkeypatch.setattr(locutor.settings, "carpeta_temp", str(tmp_path))

    class _MotorEdgeFalso(_MotorFalso):
        nombre = "edge"
        extension = "mp3"

        def __init__(self):
            super().__init__(nombre="edge", extension="mp3")

    import sys
    import types

    modulo_falso = types.ModuleType("noticia.voz.motor_edge")
    modulo_falso.MotorEdge = _MotorEdgeFalso
    monkeypatch.setitem(sys.modules, "noticia.voz.motor_edge", modulo_falso)

    guion = "Álex: hola"
    piezas = asyncio.run(locutor.procesar_guion_a_audio(guion))

    assert len(piezas) == 1
    assert piezas[0].endswith(".mp3")


def test_motor_no_disponible_al_cargar_pasa_al_siguiente(tmp_path):
    class _MotorNoCarga(_MotorFalso):
        async def cargar(self):
            raise MotorNoDisponible("no hay modelo")

    principal = _MotorNoCarga(nombre="principal")
    secundario = _MotorFalso(nombre="secundario")
    bloques = {"espana": "Álex: hola"}
    resultado = asyncio.run(locutor.locutar_episodio(bloques, [principal, secundario], tmp_path))
    assert resultado.motores_usados["secundario"] == 1
    assert "principal" not in resultado.motores_usados


def test_turno_es_instancia_de_dataclass_compartida():
    turnos, _ = locutor.parsear_turnos("Álex: hola", "intro")
    assert isinstance(turnos[0], Turno)
