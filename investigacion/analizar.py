# ruff: noqa: E501
"""Métricas agregadas de transcripciones (subtítulos automáticos) de podcasts.

Uso: python -I investigacion/analizar.py [carpeta_transcripciones] > investigacion/resultados.json

Los subtítulos automáticos no marcan quién habla, así que aquí NO se infieren turnos:
solo se miden ritmo, frases, muletillas, preguntas, transiciones y estructura temporal.
Solo se vuelcan agregados (nunca texto de los originales).
"""

import json
import re
import statistics as st
import sys
from collections import Counter
from pathlib import Path

RAIZ = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).parent / "transcripciones"

TS = re.compile(r"(\d+):(\d+):(\d+),(\d+) --> (\d+):(\d+):(\d+),(\d+)")

# Etiquetas de formato por canal (para separar tertulia / entrevista / narración)
FORMATO = {
    "wildproject": "tertulia de actualidad (3+ personas)",
    "pizarritas": "tertulia de fútbol (2-3 personas)",
    "buscatelavida": "tertulia de negocios",
    "spicy4tuna": "tertulia/entrevista de negocios",
    "worldcast": "entrevista",
    "urisabat": "entrevista (narración propia del presentador)",
    "rocaproject": "entrevista",
    "tengounplan": "entrevista",
}

MULETILLAS = [
    "o sea",
    "tío",
    "tía",
    "tío,",
    "bueno",
    "mira",
    "a ver",
    "en plan",
    "la verdad",
    "claro",
    "vale",
    "oye",
    "joder",
    "hostia",
    "coño",
    "mogollón",
    "brutal",
    "increíble",
    "exacto",
    "totalmente",
    "de verdad",
    "te lo juro",
    "es que",
    "no sé",
    "imagínate",
    "fíjate",
    "ojo",
    "literal",
    "literalmente",
    "chavales",
    "guapos",
    "madre mía",
    "qué fuerte",
    "una locura",
]
MALSONANTES = [
    "joder",
    "hostia",
    "coño",
    "mierda",
    "puta",
    "cabr",
    "gilipoll",
    "hijo de",
    "cojones",
]
TRANSICIONES = [
    r"\bpasamos a\b",
    r"\bcambiando de tema\b",
    r"\bpor cierto\b",
    r"\bhablando de\b",
    r"\bsiguiente noticia\b",
    r"\bla siguiente\b",
    r"\botra noticia\b",
    r"\bvamos con\b",
    r"\bvamos a hablar\b",
    r"\bsiguiendo con\b",
    r"\bpor otro lado\b",
    r"\bcambiamos\b",
    r"\ben otro orden\b",
    r"\bdejando eso\b",
    r"\bnos vamos a\b",
]
GANCHOS = [
    r"\bno os vais a creer\b",
    r"\bahora (os )?cuento\b",
    r"\bo sea que\b",
    r"\bespera,? que\b",
    r"\bpero espera\b",
    r"\bahora viene\b",
    r"\bvais a flipar\b",
    r"\bantes de que\b",
    r"\bse viene\b",
    r"\bahora mismo\b",
]
PUBLI = [
    r"\bcódigo\b",
    r"\bdescuento\b",
    r"\bpatrocin",
    r"\bsuscri",
    r"\bsuscribíos\b",
    r"\blike\b",
    r"\bcampana\b",
    r"\bcomparte\b",
]


def segundos(h, m, s, ms):
    return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000


def leer(ruta: Path):
    lineas = ruta.read_text(encoding="utf-8").splitlines()
    cues, i = [], 0
    while i < len(lineas):
        m = TS.match(lineas[i])
        if m:
            g = m.groups()
            ini, fin = segundos(*g[:4]), segundos(*g[4:])
            texto = []
            i += 1
            while i < len(lineas) and lineas[i].strip():
                texto.append(lineas[i].strip())
                i += 1
            cues.append((ini, fin, " ".join(texto)))
        i += 1
    # eliminar texto repetido consecutivo (subtítulos "rodantes")
    limpio, previo = [], None
    for ini, fin, t in cues:
        if t != previo:
            limpio.append((ini, fin, t))
        previo = t
    return limpio


def frases(texto: str):
    return [f.strip() for f in re.split(r"(?<=[.?!…])\s+", texto) if f.strip()]


def contar(patron: str, texto: str) -> int:
    return len(re.findall(patron, texto))


VACIAS = set(
    "de la que el en y a los se del las un por con no una su para es al lo como más pero sus le ya o este sí porque esta entre cuando muy sin sobre también me hasta hay donde quien desde todo nos durante todos uno les ni contra otros ese eso ante ellos e esto mí antes algunos qué unos yo otro otras otra él tanto esa estos mucho quienes nada muchos cual poco ella estar estas algunas algo nosotros mi mis tú te ti tu tus ellas nosotras vosotros vosotras os mío mía míos mías tuyo tuya tuyos tuyas suyo suya suyos suyas nuestro nuestra nuestros nuestras vuestro vuestra vuestros vuestras esos esas estoy estás está estamos estáis están esté estés estemos estéis estén es son era eran fue ser tengo tiene tienen tener hacer hace hacen va vas van voy vamos fue digo dice dicen decir así ahora bueno claro vale entonces pues sí no ya o sea es que tío".split()
)


def segmentar(cues, ventana=180.0):
    """Cambios de tema por salto de vocabulario entre ventanas de 3 min (aprox.)."""
    ventanas = {}
    for ini, _, t in cues:
        ventanas.setdefault(int(ini // ventana), []).append(t.lower())
    bolsas = []
    for _, v in sorted(ventanas.items()):
        c = Counter(w for w in re.findall(r"[a-záéíóúüñ]{4,}", " ".join(v)) if w not in VACIAS)
        bolsas.append(c)

    def cos(a, b):
        num = sum(a[w] * b[w] for w in a if w in b)
        den = (sum(x * x for x in a.values()) ** 0.5) * (sum(x * x for x in b.values()) ** 0.5)
        return num / den if den else 0.0

    sims = [cos(bolsas[i], bolsas[i + 1]) for i in range(len(bolsas) - 1)]
    cortes = [i + 1 for i, s_ in enumerate(sims) if s_ < 0.25]
    n_seg = len(cortes) + 1
    total_min = len(bolsas) * ventana / 60
    return {"segmentos_aprox": n_seg, "min_por_segmento": round(total_min / n_seg, 1)}


def analizar(ruta: Path) -> dict:
    cues = leer(ruta)
    dur = max(f for _, f, _ in cues)
    texto = " ".join(t for _, _, t in cues)
    palabras = re.findall(r"[\wáéíóúüñÁÉÍÓÚÜÑ']+", texto.lower())
    n = len(palabras)
    # algunos subtítulos automáticos vienen sin puntuación: no se miden frases
    con_puntuacion = len(re.findall(r"[.?!]", texto)) > n / 60
    fr = frases(texto) if con_puntuacion else ["x"]
    lens = [len(re.findall(r"\w+", f)) for f in fr] if con_puntuacion else [0]
    low = texto.lower()
    mil = max(n, 1) / 1000

    # pausas largas entre cues: posibles cambios de turno / de tema
    pausas = [cues[k + 1][0] - cues[k][1] for k in range(len(cues) - 1)]
    pausas_largas = sum(1 for p in pausas if p >= 1.0)

    # densidad por ventanas de 5 min
    ventanas = {}
    for ini, _, t in cues:
        ventanas.setdefault(int(ini // 300), []).append(t)
    wpm_vent = [len(" ".join(v).split()) / 5 for _, v in sorted(ventanas.items())]

    trans_t = []
    for ini, _, t in cues:
        tl = t.lower()
        if any(re.search(p, tl) for p in TRANSICIONES):
            trans_t.append(ini)

    return {
        "duracion_min": round(dur / 60, 1),
        "palabras": n,
        "wpm": round(n / (dur / 60), 1),
        "wpm_ventanas_p10_p90": [
            round(st.quantiles(wpm_vent, n=10)[0], 0) if len(wpm_vent) > 3 else None,
            round(st.quantiles(wpm_vent, n=10)[-1], 0) if len(wpm_vent) > 3 else None,
        ],
        "frase_media_palabras": round(st.mean(lens), 1) if con_puntuacion else None,
        "frase_mediana": st.median(lens) if con_puntuacion else None,
        "frases_cortas_pct": round(100 * sum(1 for x in lens if x <= 5) / len(lens), 1)
        if con_puntuacion
        else None,
        "frases_largas_pct": round(100 * sum(1 for x in lens if x >= 25) / len(lens), 1)
        if con_puntuacion
        else None,
        "segmentos_tema": segmentar(cues),
        "preguntas_x1000": round(texto.count("?") / mil, 1),
        "exclamaciones_x1000": round(texto.count("!") / mil, 1),
        "pausas_1s_por_min": round(pausas_largas / (dur / 60), 1),
        "muletillas_x1000": {
            m: round(contar(r"\b" + re.escape(m) + r"\b", low) / mil, 1)
            for m in MULETILLAS
            if contar(r"\b" + re.escape(m) + r"\b", low) / mil >= 0.5
        },
        "malsonantes_x1000": round(sum(contar(p, low) for p in MALSONANTES) / mil, 2),
        "transiciones_explicitas": len(trans_t),
        "ganchos_x1000": round(sum(contar(p, low) for p in GANCHOS) / mil, 2),
        "publicidad_x1000": round(sum(contar(p, low) for p in PUBLI) / mil, 2),
        "vosotros_x1000": round(contar(r"\bvosotros\b|\bvuestr", low) / mil, 1),
        "nosotros_x1000": round(contar(r"\bnosotros\b|\bhemos\b|\bestamos\b", low) / mil, 1),
        "top_palabras_vacias_inicio_frase": Counter(
            f.split()[0].lower().strip(",.¿¡") for f in fr if f.split()
        ).most_common(8),
    }


def main():
    res = {}
    for carpeta in sorted(p for p in RAIZ.iterdir() if p.is_dir()):
        for srt in sorted(carpeta.glob("*.srt")):
            d = analizar(srt)
            d["formato"] = FORMATO.get(carpeta.name, "?")
            res[f"{carpeta.name}/{srt.stem.split('.')[0]}"] = d
    sys.stdout.reconfigure(encoding="utf-8")
    json.dump(res, sys.stdout, ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
