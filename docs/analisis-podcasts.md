# Análisis de podcasts favoritos y qué aprender para el guion de NoticIA

Fecha: 2026-11-03 · Investigación en un worktree propio (sin cambios en el comportamiento por defecto).
Propuesta concreta de cambios y muestra de guion nuevo: [`propuesta-guion-tertulia.md`](propuesta-guion-tertulia.md).

> Alcance y límites. Se han analizado **subtítulos automáticos** de YouTube (no el audio) de 25 episodios.
> Esos subtítulos **no marcan quién habla**, así que no se han inferido turnos: no hay forma fiable de hacerlo
> (la puntuación aparece de forma irregular y un episodio, el #315 de The Wild Project, viene sin puntuar).
> Todo lo que sigue son agregados de ritmo, vocabulario y estructura, más lectura cualitativa de aperturas,
> cierres y fragmentos. Los transcritos son contenido de terceros: están en `investigacion/transcripciones/`
> (ignorada por git) y este documento solo contiene descripciones de técnica y ejemplos propios.
> Las métricas "por tema" son heurísticas (salto de vocabulario entre ventanas de 3 min), no cortes reales.

## 1. Qué se ha analizado

| Canal | Formato | Episodios | Por qué está |
|---|---|---|---|
| The Wild Project | Tertulia de actualidad, 3+ personas, 4-5 h | 7 (#315, #333, #351, #367, #371, #381, #386) | Es el formato objetivo de NoticIA |
| Pizarritas | Tertulia/análisis de fútbol, 2-3 voces | 3 | Referente de fútbol |
| Búscate la vida | Tertulia de negocios, 2 h | 3 | Negocio con humor y desahogo |
| spicy4tuna | Negocio de internet/YouTube, mezcla tertulia y entrevista | 2 | Explicación de negocio con gancho |
| Worldcast | Entrevista larga | 3 | Registro crudo y directo |
| Uri Sabat | Entrevista con narración propia al inicio | 2 | Cómo narra |
| Roca Project | Entrevista/historia personal | 3 | Cómo narra |
| Tengo un plan | Entrevista de divulgación | 2 | Cómo narra |

Nota: de The Wild Project se eligieron solo tertulias de actualidad (el #344 no tenía subtítulos automáticos en
español y se sustituyó por el #315, que viene sin puntuar: cuenta para duración y vocabulario, no para frases).
Se descartaron los episodios 1 contra 1 (entrevistas) a petición del usuario. Los canales de entrevista (Worldcast, Uri Sabat, Roca
Project, Tengo un plan) **no son tertulia**: sirven para aprender narración y explicación, y se tratan aparte
en el apartado 6.

## 2. Números (subtítulos automáticos)

Medias por canal. `Palabras/min` es ritmo de habla real; `Frase media` está calculada solo en los episodios con
puntuación; `Min/tema` es la longitud aproximada de un tema antes de que cambie el vocabulario.

| Canal | Duración media | Palabras/min | Frase media (palabras) | Frases ≤5 palabras | Min/tema | Preguntas /1000 pal. | Palabras fuertes marcadas /1000 pal.* |
|---|---|---|---|---|---|---|---|
| The Wild Project (n=7) | 279 min | 196 | 13,8 | 33 % | 4,4 | 11 | 1,0–2,7 |
| Búscate la vida (n=3) | 125 min | 192 | 11,0 | 37 % | 5,0 | 23 | 2,0–3,8 |
| Pizarritas (n=3) | 35 min | 212 | 23,5 | 20 % | 8,8 | 4 | 0 |
| spicy4tuna (n=2) | 126 min | 213 | 16,6 | 25 % | 5,8 | 14 | 0,8–1,0 |
| Worldcast (n=3) | 89 min | 185 | 18,7 | 23 % | 4,8 | 9 | 0–0,5 |
| Roca Project (n=3) | 100 min | 167 | 17,3 | 29 % | 4,9 | 13 | 0–0,7 |
| Uri Sabat (n=2) | 113 min | 164 | 17,8 | 25 % | 3,7 | 9 | 0 |
| Tengo un plan (n=2) | 120 min | 188 | 20,0 | 24 % | 4,2 | 12 | 0–0,6 |
| **NoticIA (prueba tertulia 29/10)** | ~60 min de guion (9.400 pal.) | — | 9,7 | — | — | 4 | 0 |
| **NoticIA (prueba telediario 03/11)** | ~14 min (2.200 pal.) | — | 11,2 | — | — | **0** | 0 |

\* Los subtítulos automáticos censuran las palabras fuertes con una marca (`[ __ ]`); se cuenta esa marca. Es un
mínimo: lo que el reconocedor no marca no aparece. En las tertulias sale una palabra fuerte cada 300-700 palabras.

Datos del guion propio (turnos sí están marcados): tertulia 29/10 = 485 turnos, 19,4 palabras por turno de media
(mediana 19), 29 % de turnos de ≤12 palabras. Telediario 03/11 = 44 turnos, **49 palabras por turno**, 20 % de
turnos cortos, cero preguntas y cero exclamaciones.

### Duraciones por tramo (tertulias de actualidad, estimación a partir de lecturas de aperturas y cierres; no medidas)

| Tramo | The Wild Project | Búscate la vida | NoticIA hoy |
|---|---|---|---|
| Teaser / promo antes del arranque | 0:30-1:30 | 1-2 min de charla suelta | no existe |
| Saludo + sumario de temas | 3-6 min | 2-5 min | ~30 s |
| Tema individual | 4-6 min | 5-8 min | 1-3 min por noticia |
| Tema "estrella" | 15-30 min | 15-25 min | no existe |
| Cierre (agradecimientos, anuncio, chiste final) | 2-5 min | 2-4 min | ~1 min |
| Total | 3,5-5 h | 1,5-2,5 h | ~60 min (2 h máx. previstas) |

## 3. Estructura y escaleta: qué se repite

1. **Teaser antes de empezar.** En los episodios de tertulia hay un arranque previo, un avance de lo que viene (un
   anuncio propio, un par de temas gordos). Luego una señal clara de comienzo ("comenzamos"). En entrevistas
   (Uri Sabat, Worldcast) el patrón es otro: un *montaje de 4-6 frases potentes del episodio* antes de presentar
   al invitado.
2. **Sumario con promesa.** El presentador enumera los temas con adjetivos fuertes ("conspiraciones", "historias
   locas") y avisa de lo que no va a caber. Crea expectativa y orienta al oyente.
3. **Calentamiento de tertulia.** Antes de la primera noticia hay unos minutos de charla suelta: bromas internas,
   un reto entre los de la mesa, pullas. Es lo que convierte "unos que cuentan noticias" en "unos amigos".
4. **Temas encadenados por asociación, no por menú.** Una noticia lleva a otra por un hilo (un atentado → "otros
   líderes a los que han intentado matar" → anécdota local → siguiente). Las transiciones explícitas
   ("hablando de…", "seguimos con temas gordos") existen, pero lo habitual es que el propio tema abra la puerta.
5. **Cada tema dura 4-6 minutos de media**, con un par de temas estrella que se alargan mucho. Un tema entra,
   se opina, se desvía a una anécdota y se cierra con un remate o una frase de opinión.
6. **Cierre suelto.** Agradecimientos, adelanto del próximo contenido, y casi siempre un último chiste o un
   comentario sobre lo que ha durado el episodio. Nunca un "resumen" formal de todo lo dicho.

## 4. Cómo explican una noticia (patrón común)

Receta que se repite en los que más gustan (descrita con palabras propias):

1. **Gancho personal o de choque en la primera frase** ("esto es real", "yo estuve ahí hace poco") antes que el dato.
2. **Dato duro en una o dos frases** (quién, qué, cuándo, cifra). Sin párrafos de contexto.
3. **Reacción del otro**: una pregunta de duda ("¿pero eso es verdad?"), una broma, o un "cuéntame".
4. **Contexto bajo demanda**: los antecedentes llegan cuando alguien los pide o cuando refuerzan una opinión,
   no en bloque al principio.
5. **Opinión con postura y discrepancia** (se contradicen, uno se deja convencer).
6. **Giro personal o comparación cercana** (un viaje, una experiencia, algo de España) que baja el tema a tierra.
7. **Remate** (broma, frase de opinión, pregunta abierta) y salto al siguiente.

En Pizarritas (más técnico, menos humor) el patrón es otro: una sentencia clara por equipo/jugador ("un cero
rotundo para la defensa"), la evidencia táctica por partes (qué falló, en qué jugada, por qué) y una frase del
protagonista o del entrenador como prueba. Menos preguntas, frases más largas (23 palabras), mucha enumeración.

## 5. Ritmo y reparto de la palabra

- **Velocidad**: 185-215 palabras/min en tertulia; el habla se solapa y no hay silencios. En entrevistas 165-190.
  Pizarritas es el más denso (212).
- **Frases**: en tertulia la media es de 11-14 palabras y 1/3 de las frases tiene ≤5 palabras (reacciones,
  asentimientos, muletillas). Aun así, ~28 % de las frases de The Wild Project tienen ≥25 palabras (los turnos de
  explicación), compensadas por las muchas frases cortas: **la clave es la mezcla, no la media**.
- **Reparto**: no se puede medir con subtítulos. De la lectura: hay un **anfitrión que reparte la palabra**,
  lanza el tema y cierra; los demás intervienen con anécdotas largas (30-90 s) y reacciones muy cortas. Las
  anécdotas largas se rompen con interrupciones de 1-3 palabras.
- **Muletillas frecuentes** (por 1000 palabras, medias en tertulia): "o sea" 5-6, "bueno" 3-5, "es que" 3-5,
  "claro" 3-5, "tío" 1-7, "vale" 2-4, "a ver" ~1,5. Sirven para pensar en voz alta y suenan a conversación real;
  usadas a ráfagas, no una por frase.
- **Risas y reacciones**: 1-3 risas marcadas por 1000 palabras en tertulia; casi ninguna en entrevistas serias.
- **Publicidad en el discurso**: casi inexistente en el audio de estos subtítulos (≤0,4 por 1000 palabras).
  NoticIA no necesita imitarla.

## 6. Narración de los favoritos de narración (Uri Sabat, Roca Project, Tengo un plan, Worldcast)

No son tertulia, pero de ellos se aprende **cómo se cuenta**:

- **Frase inicial que es una afirmación fuerte o una pregunta contraintuitiva**, y luego se desmonta
  ("todo funciona al revés de lo que crees").
- **Montaje inicial de 4-6 ganchos** (frases cortas, cada una una idea que apetece escuchar) antes del saludo.
- **Preguntas de 8-15 palabras** que piden una historia, no un dato. El invitado explica con **una imagen o
  ejemplo concreto** por idea.
- **Estructura en capas**: pregunta → historia breve → idea general → pregunta nueva. Cada 3-5 min hay un
  cambio de capítulo (la métrica sale en 3,7-4,9 min por tema).
- **Voz del presentador cálida**: repetición de "claro", "vale", "qué bueno" como acompañamiento mientras
  el otro habla.

Para NoticIA lo útil es el *montaje de ganchos* (teaser), las *preguntas que piden historia* y la *estructura en
capas* dentro de cada bloque.

## 7. Qué tienen en común los que más le gustan al usuario (según sus propias palabras)

| Preferencia dicha | Qué técnica la produce |
|---|---|
| "tertulia, es el estilo que quiero" | calentamiento entre amigos, reacciones muy cortas, temas por asociación, discrepancia real |
| "lo crudo que habla" | palabras fuertes a ráfagas (cada pocos cientos de palabras), opiniones sin filtro, hablar de lo incómodo sin eufemismos |
| "me gusta cómo narra" | frase inicial con gancho, ejemplo concreto, preguntas que piden historia, ritmo con frases cortas y largas mezcladas |
| "saben de negocio/fútbol" | datos concretos, números, un caso real por cada idea, tecnicismo explicado en una frase |

## 8. Comparación con el guion actual de NoticIA

| Aspecto | Referentes (tertulia) | NoticIA tertulia 29/10 | NoticIA telediario 03/11 |
|---|---|---|---|
| Longitud de turno | mezcla de reacciones de 1-3 palabras y anécdotas de 60-200 palabras | 19 pal. de media, mediana 19, casi todos del mismo tamaño | 49 pal. de media, turnos muy parejos |
| Frases cortas (≤5 pal.) | ~33 % | no medido; frase media 9,7 | frase media 11,2 |
| Preguntas /1000 pal. | 11-23 | 4 | **0** |
| Exclamaciones | presentes (risas, "¡no!") | pocas | **0** |
| Muletillas | "o sea", "es que", "claro", "bueno", "tío" | evitadas por regla | ninguna |
| Registro crudo | palabras fuertes cada 300-700 pal. | ninguno | ninguno |
| Apertura | teaser + sumario con promesa + calentamiento | saludo + una noticia | "Primer titular…" (sumario seco) |
| Transiciones | por asociación, con chiste | por bloque | fórmula ("Pasamos a…", "Cambiamos de terreno…") repetida |
| Discrepancia | real, sostenida | existe | ausente (todo es lectura de agencia) |
| Contexto | bajo demanda | en dos frases antes de la noticia | ausente, solo "falta por saber…" |
| Giros personales | anécdota propia de cada tertuliano | poco | ninguno |
| Cierre | chiste + adelanto + comentario sobre la duración | resumen + CTA | "esto es todo en el bloque…" |

Lo del telediario es útil como formato **alternativo** (informativo) pero no tiene nada de la tertulia que el
usuario quiere: es lectura de titulares con turnos largos y formales. Lo de la tertulia del 29/10 va por buen
camino en tamaño de turno, pero falta variar la longitud, subir las preguntas, añadir calentamiento y los
"remates" de cada tema.

## 9. Lo que NO conviene copiar (riesgos)

- **Insultos a personas concretas, rumores y bulos.** Los referentes mezclan opinión, chisme y a veces
  afirmaciones sin verificar ("el caso de X", acusaciones). En NoticIA los hechos salen del briefing y de las
  noticias; las opiniones son de los personajes y nunca se acusa a una persona identificable de algo no
  publicado. Lo crudo se aplica a **cosas, situaciones, instituciones y a sí mismos** (humor autodespectivo),
  no a un particular.
- **Contenido sobre muertes y víctimas.** Las tertulias hablan de sucesos con cachondeo; NoticIA ya tiene una
  regla de empezar serios cuando hay víctimas (accidente de Urda, 29/10). Se mantiene: se baja el tono.
- **Teorías de conspiración y pseudociencia** (frecuentes en alguno de los canales): si aparecen en noticias,
  alguien debe marcarlo como "sin base" en la misma intervención.
- **Imitar a personas o canales reales.** Las reglas y prompts describen patrones, no nombran ni imitan a nadie
  (hay un test que lo comprueba). Este documento sí puede nombrar los canales; `reglas/` y `generador.py` no.
- **Ritmo de 4-5 horas.** Es parte de su formato; en un podcast diario el equivalente es "un tema estrella" y
  "temas rápidos", no más tiempo.

## 10. Resumen de hallazgos en 8 líneas

1. Tertulia ≠ lectura de noticias: el calentamiento y la bromita previa valen tanto como la noticia.
2. Teaser + sumario con promesa abren; un chiste y un adelanto cierran.
3. Cada noticia: gancho → dato → reacción → contexto bajo demanda → opinión con postura → giro personal → remate.
4. Variedad de turno: muchas reacciones de 1-3 palabras con alguna explicación larga de 60-150 palabras.
5. Preguntas de verdad (11-23 por 1000 palabras) mueven la charla; hoy NoticIA tiene 0-4.
6. Muletillas a ráfagas ("o sea", "es que", "claro", "bueno") dan naturalidad; hoy se prohíben.
7. Registro crudo: palabras fuertes y opiniones sin filtro, pero dirigidas a cosas y situaciones, no a particulares.
8. Un tema "estrella" por episodio con 3-4 veces más tiempo que los demás da sensación de programa, no de boletín.

## 11. Reproducibilidad

- Descarga de subtítulos: `uv run --no-project --with yt-dlp yt-dlp --skip-download --write-auto-sub --sub-langs "es-orig,es" -o "investigacion/transcripciones/<canal>/%(id)s.%(ext)s" <url>`
  (con `es.*` no baja nada; hace falta pedir `es-orig`). Solo subtítulos, sin vídeo ni audio.
- Análisis: `python -I investigacion/analizar.py investigacion/transcripciones > investigacion/resultados.json`.
- Texto de un rango (para lectura): `python -I investigacion/extracto.py <srt> <ini_s> <fin_s>`.
- `investigacion/resultados.json` solo tiene agregados por episodio (sin texto de los originales).
