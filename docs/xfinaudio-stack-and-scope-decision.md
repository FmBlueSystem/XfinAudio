# XfinAudio — Decisión de Stack, Alcance y Riesgos del MVP

## Decisión oficial

XfinAudio is a metadata-driven playlist recommender, not an audio mixing engine.

En español: XfinAudio es un **recomendador offline de playlists basado en metadata**, no una app para mezclar, renderizar o procesar audio en tiempo real.

Los archivos ya fueron tratados por **Mixed In Key**, entonces el MVP debe leer esa metadata y generar playlists recomendadas.

---

## Riesgo técnico real

El riesgo ya no es detectar key/BPM/energy con DSP.

El riesgo ahora es:

```text
entender cómo Mixed In Key escribió la metadata en los archivos reales
```

Mixed In Key puede guardar datos en campos distintos según formato y software target:

- Key/Camelot: `initial key`, `TKEY`, comments, grouping o formato textual.
- Energy: puede estar en `grouping`, `comment`, `comment2` o texto combinado.
- BPM: campo estándar o tag específico del formato.
- Tags/vibe: pueden no existir o ser inconsistentes.

Por eso el primer entregable debe ser **descubrir el contrato real de metadata** con archivos del usuario.

---

## Primer entregable correcto

**Stage 1 — Mixed In Key metadata contract discovery**

Antes de implementar el parser:

1. Seleccionar 5–10 archivos reales ya procesados por Mixed In Key.
2. Leer todos sus tags con `mutagen`.
3. Documentar dónde aparecen BPM, key/Camelot, energy y tags.
4. Definir reglas de parsing tolerantes.
5. Crear fixtures de test con esas variantes.

Sin esto, el parser se construiría sobre supuestos.

---

## Stack recomendado

| Capa | Tecnología |
|---|---|
| Lenguaje | Python 3.11+ |
| Package manager | uv |
| CLI | Typer |
| Metadata audio | mutagen |
| Dominio/algoritmos | Python puro |
| Cache MVP | JSON versionado |
| Tests | pytest |
| Lint/format | ruff |
| Export | JSON, CSV, M3U |

## No usar en MVP

- Essentia
- librosa
- madmom
- C++
- DSP obligatorio
- render de audio
- crossfade / EQ / beatmatching
- stems / vocal isolation

---

## Comandos oficiales MVP

```bash
xfinaudio scan <folder>
xfinaudio recommend <folder> --strategy harmonic --export json
xfinaudio export <playlist-id> --format m3u
```

Usar `scan`, no `analyze`, porque no estamos analizando waveform; estamos leyendo metadata.

---

## Schema MVP propuesto

```json
{
  "schema_version": 1,
  "source_fingerprint": "sha256-or-file-stat-hash",
  "source_path": "track.flac",
  "metadata_source": "mixed-in-key-tags",
  "raw_tags": {
    "bpm": "124",
    "initial_key": "8A",
    "grouping": "Energy 7"
  },
  "normalized_features": {
    "title": "Track title",
    "artist": "Artist",
    "bpm": 124.0,
    "camelot_key": "8A",
    "energy": 7,
    "genre": "House",
    "tags": []
  },
  "metadata_status": "complete"
}
```

Estados posibles:

```text
complete
missing_key
missing_bpm
missing_energy
unreadable_file
unsupported_format
```

---

## Técnicas a construir ahora

| Técnica | Fuente de datos | Uso |
|---|---|---|
| Harmonic scoring | Camelot key | Ordenar tracks compatibles armónicamente |
| BPM scoring | BPM | Evitar saltos de tempo bruscos |
| Energy scoring | Mixed In Key Energy | Crear warmup, build, peak-time |
| Fuzzy scoring | key + BPM + energy + tags | Ranking global de compatibilidad |
| Tag/vibe grouping | genre/comments/grouping | Playlists por estilo o intención |
| Deterministic export | cache normalizado | Salidas repetibles JSON/CSV/M3U |

## Pesos configurables

Los pesos no deben ser mágicos. Deben vivir en config:

```json
{
  "weights": {
    "harmonic": 0.40,
    "bpm": 0.25,
    "energy": 0.25,
    "tags": 0.10
  }
}
```

Regla: si `tags` no existen o son inconsistentes, su peso debe redistribuirse o ignorarse.

---

## Cómo validar si una playlist es buena

Métrica mínima MVP:

1. Comparar contra 1–3 playlists/setlists reales armados manualmente.
2. Medir compatibilidad promedio entre tracks consecutivos.
3. Medir cantidad de saltos fuertes de BPM/energy.
4. Revisar manualmente top 3 playlists generadas.
5. Registrar feedback y ajustar pesos.

Sin esta validación, el recomendador no tiene criterio de mejora.

---

## Arquitectura recomendada

```text
Audio folder
  → metadata contract discovery
  → metadata reader
  → feature normalizer
  → versioned cache
  → scoring engine
  → playlist strategies
  → exporters
```

Módulos:

```text
xfinaudio/
  cli.py
  metadata/tag_inspector.py
  metadata/mixedinkey_reader.py
  domain/track.py
  domain/camelot.py
  domain/scoring.py
  domain/recommendation.py
  cache/json_repository.py
  export/json_exporter.py
  export/csv_exporter.py
  export/m3u_exporter.py
```

---

## Fuera del MVP

| Técnica | Motivo |
|---|---|
| Phrase detection | Requiere análisis estructural o beat/downbeat data |
| Vocal clash detection | Requiere detección vocal o stems |
| Timbre similarity | Requiere DSP o embeddings de audio |
| Crossfade/EQ | Pertenece a mezcla/render |
| Time-stretch/pitch-shift | DSP avanzado |
| Audio rendering | Cambia el producto de recomendador a mixer |

---

## Bibliografía y referencias

1. Mixed In Key — Harmonic Mixing Guide. Base práctica para Camelot Wheel, harmonic mixing y energy level.  
   https://mixedinkey.com/harmonic-mixing-guide/

2. Mixed In Key — Software principal. Referencia de producto para key/BPM/energy como metadata DJ.  
   https://mixedinkey.com/

3. Mutagen documentation. Librería Python para leer tags MP3, FLAC, MP4/M4A, Ogg, AIFF.  
   https://mutagen.readthedocs.io/

4. Typer documentation — CLI y testing con `CliRunner`.  
   https://typer.tiangolo.com/  
   https://typer.tiangolo.com/tutorial/testing/

5. pytest documentation. Testing/TDD para Python.  
   https://docs.pytest.org/

6. Ruff documentation. Lint/format rápido para Python.  
   https://docs.astral.sh/ruff/

7. uv documentation. Python package/project manager moderno.  
   https://docs.astral.sh/uv/

8. Vande Veire et al. — “From raw audio to a seamless mix”. Referencia de contraste: XfinAudio NO sigue el camino de mezcla/DSP.  
   https://link.springer.com/article/10.1186/s13636-018-0134-8

---

## Conclusión

Construir primero:

```text
Mixed In Key metadata contract → parser tolerante → cache → recommender → exports
```

No existe en el roadmap:

```text
DSP → C++ → mezcla → render → beatmatching → análisis de waveform
```

---

## Algorithm Coverage Matrix

| Algorithm / Technique | Source | Status | Reason | Spec/task location |
|---|---|---|---|---|
| Camelot rigid compatibility | Harmonic docs | NOW | Uses Mixed In Key key only | Stage 3 |
| Fuzzy keymixing / Camelot diagonals | Review + prior research | NOW | No DSP; improves harmonic recommendations | Stage 3 |
| BPM compatibility | Scope docs | NOW | Uses Mixed In Key BPM | Stage 3 |
| Energy curve scoring | Scope docs | NOW | Uses Mixed In Key energy | Stage 4 |
| Controlled energy boost | Harmonic docs | NOW | Configurable harmonic/energy rule | Stage 3/4 |
| Weighted fuzzy scoring | Scope docs | NOW | Combines key/BPM/energy/tags | Stage 3 |
| Tag/vibe grouping | Scope docs | NOW if reliable | Depends on tag quality | Stage 4 |
| Deterministic ordering | Review | NOW | Required to produce playlists, not just pair scores | Stage 3 |
| Held-Karp exact sequence optimizer ≤20 | Prior SDD/review | NOW | No DSP; exact ordering for small sets | Stage 3 |
| Greedy + 2-opt optimizer >20 | Prior SDD/review | NOW | No DSP; scalable ordering | Stage 3 |
| Warmup strategy | Scope docs | NOW | Product playlist strategy | Stage 4/spec scenario |
| Peak-time strategy | Scope docs | NOW | Product playlist strategy | Stage 4/spec scenario |
| Same-energy strategy | Scope docs | NOW | Product playlist strategy | Stage 4/spec scenario |
| Same-vibe strategy | Scope docs | NOW if tags reliable | Product playlist strategy | Stage 4/spec scenario |
| Tonnetz / TPS tonal distance | Prior research/review | LATER | No DSP, but advanced harmonic model | Future SDD change |
| Key detection | Prior research | OUT | Provided by Mixed In Key | Explicit non-goal |
| BPM/beat tracking | Prior research | OUT | BPM provided by Mixed In Key; beat tracking not needed | Explicit non-goal |
| Downbeat tracking | Prior research | OUT | No mixing/phrase alignment product scope | Explicit non-goal |
| Cue point detection | Prior research | OUT | No mixing product scope | Explicit non-goal |
| Phrase/structural segmentation | Prior research | OUT | Requires audio structure; not playlist MVP | Explicit non-goal |
| Timbre similarity / embeddings | Prior research | OUT | Requires DSP/embeddings | Explicit non-goal |
| Vocal clash detection | Prior research | OUT | Requires vocals/stems or DSP | Explicit non-goal |
| Mashability beat-synchronous | Prior research | OUT | Requires beat/chroma/audio analysis | Explicit non-goal |
| Crossfade/EQ/render/time-stretch | Prior research | OUT | Mixing/render product, not recommender | Explicit non-goal |
| GAN transitions | Prior research | OUT | Not aligned to product | Explicit non-goal |

## Sequence optimizer decision

A playlist recommender needs a sequence optimizer. Pairwise scoring alone is insufficient.

Decision:

```text
≤20 tracks: Held-Karp exact optimizer
>20 tracks: greedy seed + 2-opt refinement
```

The optimizer maximizes transition score between consecutive tracks.

## Fuzzy keymixing clarification

There are two different fuzzy concepts:

1. **Fuzzy keymixing**: extra Camelot-compatible moves, including diagonals like `2A → 1B / 3B`.
2. **Weighted fuzzy scoring**: combining harmonic, BPM, energy and tag scores.

Both are in scope.

---

## New requirement: Serato export

XfinAudio must support exporting a recommended playlist to Serato as a **crate**.

Open-source release safety policy:

- Do not mutate the Serato library/database blindly.
- Prefer creating a Serato-compatible crate/export artifact.
- If writing into Serato's library structure is supported, require:
  - dry-run preview;
  - backup of affected Serato files;
  - explicit user confirmation;
  - validation that Serato can read the created crate;
  - rollback instructions.

Requirement name:

```text
serato-crate-export
```

Expected UX:

```text
Select recommended playlist → Export → Serato Crate → choose crate name → preview → create
```

This is a product-aligned future/export feature. It does not require DSP, C++, or audio rendering.

---

## DJ assistant requirements

XfinAudio is a GPL-3.0-only full open-source desktop tool to support DJs in generating playlists. It should assist the DJ, not replace them.

Binary/app bundle redistribution, PySide6/Qt, mutagen, signing/notarization/DMG, and third-party dependencies still require release-specific legal review. No legal clearance is implied.

### Explainability

Every recommendation must explain why it was made:

```text
Track A → Track B
Key: compatible 0.90
BPM: close 0.95
Energy: smooth build 0.80
Tags: same vibe 0.70
Final score: 0.88
```

### DJ intent modes

The user must be able to choose the playlist intent:

- warmup;
- build;
- peak-time;
- chill;
- same-energy;
- same-vibe;
- harmonic journey.

### Manual DJ control

The user must be able to:

- lock a track in the playlist;
- exclude tracks;
- set starting track;
- set ending track;
- manually reorder tracks;
- regenerate around locked choices;
- adjust scoring weights.

### Product persistence

Use SQLite for product persistence and versioned settings for configuration.

```text
SQLite: tracks, playlists, scores, exports, scan history
settings: weights, strategy defaults, UI preferences, export paths
```

### Serato validation

Before shipping Serato export, run a dedicated crate-format validation spike.

Policy:

```text
research → dry-run → backup → confirm → create → validate → rollback path
```
