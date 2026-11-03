# Propuesta: guion de NoticIA más cercano a una tertulia

Basada en [`analisis-podcasts.md`](analisis-podcasts.md). **Es solo una propuesta**: no se ha cambiado
`reglas/` ni `src/noticia/generador.py`. Cada cambio está escrito para poder pegarse tal cual. Las
reglas y prompts describen patrones; no nombran ni imitan a personas ni podcasts reales (hay un test que lo
vigila en `tests/test_config.py`).

## 1. Cambios en `reglas/instrucciones.md`

### 1.1 Sustituir el apartado "RITMO Y ESTILO DE TERTULIA" por

```markdown
# RITMO Y ESTILO DE TERTULIA:
1. **Mezcla de turnos.** Muchas reacciones de 1-4 palabras ("¿en serio?", "qué bueno", "no me jodas") y, de vez
   en cuando, una explicación o anécdota de 60-120 palabras que el otro rompe con una interrupción. Que no
   todos los turnos midan lo mismo.
2. **Cada noticia sigue este hilo (sin que se note la plantilla):** gancho en la primera frase → el dato duro en
   una o dos frases → reacción o duda del otro → contexto solo cuando lo pide la charla o refuerza una opinión →
   opinión con postura y discrepancia → un giro cercano (algo de España, de la vida diaria) → remate (broma o
   pregunta abierta) y salto.
3. **Las preguntas de verdad mueven la charla.** Al menos una pregunta cada 4-5 turnos ("¿pero eso a quién
   afecta?", "¿eso es verdad o es titular?"). Quien pregunta no sabe la respuesta de antemano.
4. **Muletillas a ráfagas, no una por frase.** Se admiten "o sea", "es que", "claro", "bueno", "a ver", "mira" y
   un "tío" ocasional como forma de pensar en voz alta. Evitad las frases de locutor ("sin más dilación",
   "pasamos a", "cambiamos de terreno").
5. **Transiciones por asociación.** El siguiente tema entra porque el anterior lo evoca ("hablando de gente que
   se lía con el dinero…") o por una broma, no con un anuncio de bloque.
6. **Calentamiento y bromas internas.** Un par de pullas entre ellos, una referencia compartida y una
   discrepancia pequeña antes de entrar en materia hacen que se note que son amigos.
7. **Opiniones claras.** Cada uno se moja, discrepa con argumentos y, si hace falta, se deja convencer.
8. **Un tema estrella por episodio.** De todo el bloque, uno se trata con el triple de tiempo y más debate; el
   resto, rápido.
```

### 1.2 Nuevo apartado "REGISTRO DIRECTO" (el pedido por el usuario: crudo, sin filtro)

```markdown
# REGISTRO DIRECTO (CRUDEZA CON CRITERIO):
- Se habla claro y sin eufemismos: palabras fuertes de cuando en cuando ("joder", "menuda mierda", "qué
  cabronada", "es una vergüenza") y opiniones sin filtro sobre decisiones, instituciones, empresas, modas y
  situaciones. Una palabra fuerte cada tres o cuatro turnos como mucho; si aparece en todos, deja de sonar natural.
- **Dirigido a cosas, no a particulares.** Se critica lo que se hace o se decide, no se insulta a una persona
  concreta ni se la acusa de algo que no esté en las noticias. Para dudas, "según la noticia" o "dicen que".
- Humor autodespectivo y entre ellos: sí. Burla de víctimas, de enfermos o de colectivos vulnerables: no.
- Nada de rumores ni bulos: lo que no está en el briefing o en las noticias no se afirma. Si una noticia es
  una teoría sin base, uno lo dice en la misma intervención.
- Si hay víctimas o fallecidos, el tono baja primero y la crudeza se queda para lo que haya de escándalo o de
  fallo, no para el dolor.
```

### 1.3 Sustituir en "REGLA DE ORO DE CONTEXTO"

Cambiar "explicad en dos frases el marco general" por: "El contexto llega **bajo demanda**: dad primero el dato y
una reacción, y aportad antecedentes cuando alguien los pida o cuando sirvan para sostener una opinión. Nunca
más de dos frases seguidas de contexto sin que el otro intervenga."

### 1.4 Ajustes menores
- En "Naturalidad", quitar "Evitad muletillas robóticas" y dejar solo "Evitad frases hechas de locutor y repetir
  la estructura de un turno". Las muletillas humanas se permiten (ver 1.1).
- En "FORMATO", añadir: "Los turnos de reacción (1-4 palabras) van como línea propia: `Álex: ¿En serio?`."
  (el motor de voz ya procesa líneas cortas).

## 2. Cambios en `reglas/contexto.md`

Añadir al final de "Reglas de estilo":

```markdown
- Cada bloque tiene una noticia estrella (la de más interés para el oyente) con más tiempo y debate; las demás,
  rápidas.
- Se abre con un teaser de 2-3 frases que prometen lo mejor del día, un calentamiento corto entre los de la mesa y
  el sumario; se cierra con una bromita, un adelanto de mañana y la despedida (sin resumir lo dicho).
- Humor y crudeza se aplican a situaciones e instituciones, nunca a particulares ni a víctimas.
```

## 3. Cambios en los perfiles de personaje (`reglas/personaje_*.md`)

Añadir un tic distintivo a cada uno para que se noten dos voces:

- **Álex**: cuando se entusiasma, alarga la anécdota y suelta un "espera, que esto es lo mejor"; sus
  muletillas son "o sea" y "mira". Se indigna con la política con palabras más gruesas ("es una tomadura de pelo").
- **Santi**: reacciona en una línea ("ya, ya", "ajá", "claro, claro") y remata con un chiste seco de una frase. Su
  tic es el "es que…" seguido de una objeción. La crudeza suya es la ironía ("menuda joya").
- **Invitada**: aporta el dato que cierra la discusión ("a ver, los números dicen otra cosa"); cuando dice una
  palabra fuerte se nota y hace reír por contraste con su tono.

## 4. Cambios en `src/noticia/generador.py` (propuesta, sin aplicar)

### 4.1 `construir_bloque_con_contexto` — instrucciones

Sustituir el bloque `INSTRUCCIONES:` por:

```python
    INSTRUCCIONES:
    - Es una tertulia entre amigos, no un informativo. Cada personaje habla según su perfil.
    - Elegid UNA noticia estrella del bloque (la más interesante para un oyente español) y dadle
      el triple de tiempo y debate; las demás, rápidas.
    - Cada noticia: gancho en la primera frase, dato duro en una o dos frases, reacción o duda del
      otro, contexto solo si hace falta, opinión con discrepancia, remate o pregunta abierta. No
      enumeréis esos pasos: que se note solo.
    - Mezclad turnos: muchas reacciones de 1-4 palabras en línea propia y alguna explicación de
      60-120 palabras que el otro interrumpe. Que no todos los turnos midan lo mismo.
    - Al menos una pregunta cada 4-5 turnos. Muletillas ("o sea", "es que", "claro", "bueno") a ráfagas.
    - Pasad de un tema al siguiente por asociación o con una broma, sin fórmulas ("pasamos a…").
    - Usad los datos del BRIEFING como munición para opinar, no para dar una clase.
    - Charlad durante 8-10 minutos de forma apasionada.
    - DESCARTAD sin comentarla cualquier noticia de la lista que en realidad sea
      publicidad, una promoción, un cupón de descuento o contenido comercial, o
      que no tenga interés real para una audiencia española: no forméis parte de
      su promoción.
```

El resto del prompt (formato de respuesta, sin markdown) no cambia.

### 4.2 `generar_intro`

Sustituir la tarea por:

```python
        f"Hoy es {fecha_texto}. "
        f"TAREA: Genera la apertura con este sumario de temas: {resumen_titulares}. "
        "Estructura: (1) un teaser de 2-3 frases que prometa lo mejor del día, (2) un calentamiento "
        "corto y gracioso entre los de la mesa (una pulla, una discrepancia pequeña), (3) el saludo "
        "y la presentación del episodio, (4) el sumario con adjetivos y promesas, sin leer titulares secos. "
        "Si hay invitada, se la presenta con un par de frases de cachondeo cariñoso. "
        "Responde ÚNICAMENTE con el diálogo, sin preámbulo ni markdown."
```

### 4.3 `generar_outro`

```python
        "TAREA: Genera la despedida: una pulla o broma final, un adelanto de mañana si procede, "
        "y un cierre breve que recuerde dos o tres de estos titulares reales de hoy "
        f"(no os inventéis otros):\n{resumen_titulares}\n"
        "Nada de resumen formal ni de 'esto es todo'. Termina con la despedida: NoticIA. "
        "Responde ÚNICAMENTE con el diálogo, sin preámbulo ni markdown."
```

### 4.4 `generar_briefing_contexto`

Añadir un punto 5 para fabricar giros cercanos: *"5. Un giro cercano: qué cambia esto en la vida diaria de un oyente
en España, o una comparación con algo que conozca."* Esto alimenta el "giro personal" del hilo de cada noticia.

### 4.5 Validación opcional (código nuevo)

Para vigilar que el guion no vuelve a sonar a telediario, un test barato con el guion generado:
`test_guion_tiene_variedad_de_turnos` (≥25 % de turnos de ≤6 palabras, ≥1 pregunta cada 8 turnos, ningún
turno de >180 palabras). No se ha implementado: depende de decidir si el usuario quiere el cambio.

## 5. Efecto esperado frente al guion actual

| Métrica | Hoy (tertulia 29/10) | Hoy (telediario 03/11) | Objetivo propuesto |
|---|---|---|---|
| Palabras por turno | 19 (todos parejos) | 49 | mediana ≤12, con algún turno de 60-120 |
| Turnos de ≤6 palabras | casi ninguno | ~0 | ≥25 % |
| Preguntas /1000 pal. | 4 | 0 | 10-20 |
| Muletillas | prohibidas | ninguna | 3-6 /1000 pal. |
| Apertura | saludo y noticia | sumario seco | teaser + calentamiento + sumario |
| Cierre | resumen + CTA | "esto es todo" | broma + adelanto + despedida |
| Palabras fuertes | 0 | 0 | 1 cada 3-4 turnos como máximo, dirigidas a cosas |

## 6. Muestra de guion nuevo (bloque Friki, ~3 min)

Datos tomados de `output/episodios/2026-11-03/noticias.json` (solo titulares, sin inventar cifras ni
hechos): Nintendo visitó museos y fabricó tejidos propios para la túnica de Link en el remake de Zelda:
Ocarina of Time; se confirman juegos nuevos en Switch y Switch 2; se han publicado las notas de la prensa de
Stellar Blade: Complete Edition en Switch 2; llegan nuevos detalles del Área Silvestre de Pokémon GO 2026.

```text
Santi: Dime que has leído lo de la túnica de Link. Dímelo.

Álex: ¡Pero claro que lo he leído! ¿Sabes lo que hicieron en Nintendo?

Santi: Algo caro y poco práctico, seguro.

Álex: Se fueron a museos. A museos, Santi. Y fabricaron sus propios tejidos para diseñar la túnica del Zelda de
Ocarina of Time, el remake.

Santi: ¿Para una túnica verde?

Álex: Para LA túnica verde. Es el traje más famoso de los videojuegos. Imagínate que te encargan eso y no
quieres que se parezca a un disfraz de Carnaval.

Santi: Ya. O sea, que el departamento de pijama de Link hizo trabajo de campo.

Álex: Pues sí, y a mí me parece genial. Es el cariño por el detalle que hace que un remake no sea un
refrito.

Santi: Yo con que no pesen ochenta euros más… Vale, ¿y lo de Stellar Blade en la Switch 2?

Álex: Que ya hay notas de la prensa para la Complete Edition. Y ahí hay que mirar con lupa, porque son las
primeras impresiones de un port.

Santi: Es que ese es el miedo, ¿no? Que un juego que luce en otra consola llegue a la Switch 2 y vaya a
saltitos.

Álex: Pero eso depende de lo que midan. ¿Tú qué esperas, que vaya como en PS5?

Santi: No. Espero que no me lo vendan como si fuera lo mismo. Yo me conformo con una versión honesta.

Álex: Eso es verdad. Te lo compro.

Santi: Oye, y siete juegos más confirmados en las últimas horas entre Switch y Switch 2, dicen. Pero el que
quiero comentar es el nombre de uno: Silly Polly Beast.

Álex: ¡Calla, que es buenísimo!

Santi: Alguien en un despacho dijo "pongámosle Silly Polly Beast" y todos dijeron que sí.

Álex: ¡Qué va, seguro que hubo discusión!

Santi: Seguro. Ni idea de cómo será el juego, pero el nombre ya me ha ganado.

Álex: Y ahora el de siempre: Pokémon GO. Tienen nuevos detalles del Área Silvestre 2026.

Santi: ¿Y a mí qué me cambia eso?

Álex: Si juegas… pues a salir de casa. Aunque ahora no, que hace un frío que no veas.

Santi: Ya. Cuando el entrenador sale con abrigo, el Pokémon sale con aire de "otra vez".

Álex: Eso sí. Pero el Área Silvestre es la excusa de la temporada para quedar con gente, y a mí eso me gusta.

Santi: Ahí te doy la razón. Aunque yo sigo diciendo que lo mejor de hoy es el nombre del juego.

Álex: Y yo, el traje de Link.

Santi: Y no me vengas con película de culto ahora, ¿eh?

Álex: ¡Pues claro que sí! Hoy toca una que me parece perfecta para hablar de detalle y artesanía…
```

Notas sobre la muestra:
- Las dos noticias con más sustancia (la túnica y el nombre del juego) ocupan más tiempo; las otras dos, rápidas
  ("estrella" + "rápidas").
- 28 turnos y 425 palabras (~3 min): 6 turnos de ≤6 palabras (21 %), 7 preguntas, mediana de 15 palabras por turno y
  muletillas ("o sea", "es que", "vale", "ya"). Es una muestra corta y se queda por encima del objetivo de la tabla;
  la generación real, con más margen, debe acercarse más (ver sección 5).
- La crudeza queda baja aposta (esta muestra no incluye palabras fuertes): en un bloque friki se deja para
  noticias con escándalo o fallo. Para ver la crudeza en acción, véase la muestra de España abajo.
- El enlace a la película de culto (obligatorio en el bloque friki) se deja abierto al final; en el guion real
  el generador lo desarrolla.

## 7. Muestra corta del registro directo (bloque España, 6 turnos, ficticia)

Solo para ilustrar el registro; los hechos son genéricos y no vienen de ninguna noticia real.

```text
Álex: Otra vez la inversión en infraestructuras en niveles de hace treinta años. Treinta, Santi.

Santi: Es que es una vergüenza. Y luego vendrán a decir que es culpa del tiempo.

Álex: ¡Joder, es que lo dicen!

Santi: Ya. Siempre es culpa de algo que no se puede votar.

Álex: Pero tú, ¿quién crees que lo arregla?

Santi: Quien pague la factura, y esa soy yo.
```

La crudeza va a las decisiones y a la situación, no a una persona concreta.

## 8. Decisión pendiente (usuario)

1. ¿Aplicar los cambios de `reglas/` y `generador.py` tal cual se proponen?
2. ¿Hasta dónde llevar la crudeza? (la propuesta: palabras fuertes ocasionales, nunca insultos a particulares).
3. ¿Mantener el formato "telediario" como modo alternativo?
4. ¿Probamos una generación real de un bloque con los prompts nuevos y comparamos de oído?
