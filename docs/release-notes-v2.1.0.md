# XfinAudio 2.1.0 · Consolidated changes / Cambios consolidados

Fecha: 2026-09-30. Estado: código fuente para revisión; estas notas no anuncian
un nuevo tag, release, instalador firmado ni despliegue.

## Summary

2.1.0 combines the correctness/security audit fixes with optional NaN request
interpretation and commentary across the desktop workflows. The deterministic
local engine retains selection, ordering, scoring, validation and Serato export.
AI is off by default. Python 3.12 or newer is required. See the
[AI workflow guide](ai-workflows.md) and [secure setup](ai-settings.md).

## IA opcional con decisiones musicales locales

- Biblioteca: interpretación local o remota de filtros visibles y editables;
  ningún filtro inventa BPM, tonalidad o energía ausentes.
- Crear: petición conversacional → intención editable → generación local de
  variantes. Aplicar una variante es una decisión separada.
- Revisar: hechos, transiciones y reemplazos calculados localmente; narración IA
  opcional que se debe verificar, sin alterar el set.
- Editor: abrir playlists guardadas, previsualizar cambios, aplicar al borrador y
  guardar por separado. Bloqueos, exclusiones, deshacer y borradores se preservan.
- Mis playlists: búsqueda/comparación local y selección semántica opcional con
  IDs temporales y agregados anónimos. Borrar requiere confirmación.
- Metadatos: explica faltantes y prioridades reales, sin completar ni escribir tags.
- Live: sesión manual con candidatos puntuados y revalidados localmente;
  comentario opcional, sin reordenar ni detectar reproducción.
- Ajustes: proveedor y destinatario visibles, configuración externa de credenciales,
  prueba de conexión explícita, cancelación y recuperación ante fallos.

La IA nunca recibe audio. Los datos compartidos dependen de la acción: Crear y
Revisar tienen contextos distintos de los agregados anónimos de otras pantallas.
Las rutas conocidas o reconocibles se ocultan; el texto libre aún puede contener
información privada. La activación es voluntaria y los nuevos paneles solicitan
consentimiento; un cambio de destinatario exige renovarlo. Las respuestas tardías
no deben sustituir el contexto actual. Cancelar no retira lo ya enviado.

## Correcciones acumuladas de fiabilidad y seguridad

- Credenciales del proveedor limitadas a destinos HTTPS finales, sin seguir
  redirecciones autenticadas. CSV de informes protege texto parecido a fórmulas.
- Ajustes escritos mediante reemplazo atómico; configuración dañada conservada
  para diagnóstico y recuperación visible. Durante esa recuperación se pausa la
  escritura automática de loudness.
- Conexiones SQLite cerradas explícitamente e integridad de playlists reforzada;
  migración de referencias huérfanas sin perder el orden válido.
- Cierre y cancelación drenan workers sin terminarlos a la fuerza. Generación de
  variantes en segundo plano, reintentos y protección de resultados anteriores.
- Actualizaciones de perfiles por lotes y menos puntuación redundante; estado
  desktop inmutable, recuperación del watcher y recursos de iconos/traducción
  disponibles también desde paquetes construidos.

## Motor, interfaz y exportación

- Rechazo de BPM no finito o no positivo; precisión fraccionaria visible;
  compatibilidad Camelot direccional y alcance BPM half-time corregidos.
- Selecciones obligatorias, pistas finales, bloqueos y exclusiones se conservan
  al dimensionar, secuenciar, reemplazar o completar playlists. Duraciones
  desconocidas o insuficientes se informan de forma explícita.
- Exportación directa y determinística a `_Serato_/Subcrates`, con vista previa,
  confirmación, copias recuperables, escritura atómica y validación posterior.
  No se modifica la base Serato V2 activa. Exportar un set guardado usa su orden
  exacto y nuevos informes, sin heredar exclusiones de otro set.
- Controles de aplicar, cancelar y reparar más accesibles; detalles de transición
  seleccionables con teclado; correcciones de recorte a 1000×700 y callbacks Qt
  tardíos. Traducciones españolas de controles críticos, sin prometer cobertura total.
- Empaquetado local ligado al gate del commit limpio exacto y a la integridad del
  bundle; acciones de CI fijadas a commits y descarga de FFmpeg verificada por hash.

El [informe de auditoría](reviews/2026-09-audit-remediation.md) conserva el detalle
histórico de cada corrección. Las mejoras específicas de otros exportadores DJ
quedaron fuera de esta revisión.

## Actualización y límites de verificación

- Haz copia de tus datos y configuración antes de actualizar. Antes de escanear,
  respalda los comentarios que quieras conservar o desactiva loudness: sigue
  activado por defecto y combina análisis con escritura automática de tags y
  reemplazo de comentarios. Estas mejoras no cambian esa política.
- La evidencia automatizada usa Linux/Qt offscreen, datos sintéticos y transportes
  inyectados. Consulta el gate y CI del commit exacto; estas notas no certifican
  un resultado futuro ni trasladan el QA manual histórico a este candidato.
- Siguen pendientes pruebas interactivas nativas en macOS, instalación/firma y
  notarización, accesibilidad nativa, importación real de Serato, credenciales y
  proveedor NaN reales, y evaluación musical mediante escucha.
- Los tests de contratos no prueban gusto musical ni exactitud de toda frase del
  modelo. Puedes mantener IA desactivada y usar los recorridos locales.

Licencia: GPL-3.0-only. La distribución de binarios requiere revisar las
obligaciones de dependencias; estas notas no implican aprobación legal.
