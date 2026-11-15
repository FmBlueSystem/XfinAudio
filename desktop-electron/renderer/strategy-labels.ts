/**
 * Presentation only: Spanish copy for the playlist strategies the core publishes.
 *
 * The core keeps its English `display_name`/`description` because other code and
 * the API read them; the desktop picks a Spanish name and description here by the
 * stable strategy `name`. A name this table does not know keeps the core text.
 */
export interface StrategyLabel { label: string; description: string; }
const labels: Record<string, StrategyLabel> = {
  harmonic_journey: { label: 'Viaje armónico', description: 'Prioriza el movimiento compatible en Camelot manteniendo el BPM y la energía estables.' },
  warmup: { label: 'Calentamiento', description: 'Empieza controlado, con pistas de energía baja a media.' },
  build: { label: 'Construcción', description: 'Prefiere una curva de energía que sube poco a poco.' },
  peak_time: { label: 'Hora punta', description: 'Centra la recomendación en pistas de energía alta.' },
  chill: { label: 'Relax', description: 'Prefiere pistas de energía y BPM más bajos.' },
  same_energy: { label: 'Misma energía', description: 'Límite estricto: solo pistas a ±1 nivel de energía de la pista ancla. El color se pondera pero no se limita.' },
  same_vibe: { label: 'Mismo ambiente', description: 'Da prioridad a las etiquetas y al género compartidos cuando existen metadatos de ambiente.' },
  same_color: { label: 'Mismo color', description: 'Filtro estricto: solo pistas con el color espectral de la pista ancla. La energía se pondera pero no se limita.' },
  same_genre: { label: 'Mismo género', description: 'Limita la lista al género principal dominante de las pistas ancla.' },
  same_color_energy: { label: 'Mismo color y energía', description: 'Filtros estrictos: solo pistas con el color de la pista ancla Y su nivel exacto de energía.' },
  consistent_loudness: { label: 'Sonoridad constante', description: 'Filtro estricto: las pistas medidas deben quedar dentro de la banda de sonoridad integrada configurada.' },
};
/** Spanish label and description for a known strategy name; any other name keeps the core text. */
export function localizeStrategy(strategy: { name: string; displayName: string; description: string }): StrategyLabel {
  return labels[strategy.name] ?? { label: strategy.displayName, description: strategy.description };
}
