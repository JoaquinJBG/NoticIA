# Roadmap: NoticIA Professional Edition 🎙️

Este documento marca el camino para elevar la calidad de NoticIA al nivel de los grandes podcasts de entretenimiento (como The Wild Project).

## Objetivos de Calidad
- **Engagement:** Retener al oyente desde el segundo 1.
- **Naturalidad:** Romper la estructura de "turnos" robóticos.
- **Autoridad:** Aportar datos que no están en la noticia simple.
- **Sonido:** Audio con cuerpo, presencia y dinamismo.

---

## Fases de Desarrollo (Una por Rama)

### 1. 🟢 Estructura y Hooks (`feat/estructura-hooks`)
- [ ] **Intro Épica:** Creación de una intro con música de alto impacto.
- [ ] **Sumario Dinámico:** Álex y Santi presentan los 3 temas más potentes al inicio.
- [ ] **Cierre y CTA:** Despedida profesional animando a seguir el podcast.

### 2. 🟢 Dinamismo y Solapamiento (`R-4-Dinamismo-y-solapamiento`)
- [x] **Cross-fading de voces:** Solapamiento de 250ms entre intervenciones.
- [x] **Reducción de repeticiones:** Ajuste de temperatura y prompts para evitar bucles.
- [ ] **Reacciones Cortas:** (Opcional, pospuesto por petición del usuario).

### 3. 🟢 Paisaje Sonoro Dinámico (`R-5-diseno-sonoro`)
- [x] **Música por categoría:** Cambio automático de sintonía según el tema (Serio, Animado, Neutro).
- [x] **Efecto Ráfaga:** Música con volumen alto al inicio de cada bloque para impacto.
- [x] **Transiciones suaves:** Fundidos encadenados entre bloques musicales.

### 4. ⚪ Investigación Profunda (`feat/investigacion-pro`)
- [ ] **Contexto Expandido:** Gemini genera un "briefing" de contexto antes del guion.
- [ ] **Curiosidades:** Inclusión de datos históricos o analogías pop no presentes en el RSS.

### 5. ⚪ Post-producción de Audio (`feat/mastering-audio`)
- [ ] **Mastering Digital:** Aplicar compresión y normalización de picos a la mezcla final.
- [ ] **EQ de voces:** Realzar graves y limpiar medios para mayor calidez.
