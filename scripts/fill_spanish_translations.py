#!/usr/bin/env python3
"""Populate Spanish translations in translations/xfinaudio_es.ts."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

TS_PATH = Path("translations/xfinaudio_es.ts")

# English -> Spanish translations
TRANSLATIONS: dict[str, str] = {
    # General UI
    "About XfinAudio": "Acerca de XfinAudio",
    "Quit": "Salir",
    "Help": "Ayuda",
    "Library": "Biblioteca",
    "Build Playlist": "Construir Playlist",
    "Review Mix": "Revisar Mix",
    "Export to Serato": "Exportar a Serato",
    "Metadata Worklist": "Worklist de Metadata",
    "Ready": "Listo",
    "Cancel Scan": "Cancelar Escaneo",
    "Choose Folder": "Elegir Carpeta",
    "Scan Metadata": "Escanear Metadata",
    "Not available": "No disponible",
    "yes": "sí",
    "replace with backup": "reemplazar con backup",
    "All": "Todos",
    "Complete": "Completos",
    "Incomplete": "Incompletos",
    "Untitled": "Sin título",

    # Menu / About
    "XfinAudio": "XfinAudio",
    "BlueSystem.IO Audio": "BlueSystem.IO Audio",
    "Concepto: Freddy Molina": "Concepto: Freddy Molina",
    "Versión 1.0": "Versión 1.0",
    "Metadata-driven DJ playlist assistant powered by harmonic mixing. Built with PySide6 and open-source under GPL-3.0-only.":
        "Asistente de playlists DJ basado en metadata y harmonic mixing. Construido con PySide6 y open-source bajo GPL-3.0-only.",
    "Mixed In Key®, Camelot®, and Camelot System® are trademarks of Mixed In Key LLC. Serato™ and Serato DJ Pro™ are trademarks of Serato Limited. All other trademarks are property of their respective owners. XfinAudio is an independent project with no affiliation to these companies.":
        "Mixed In Key®, Camelot® y Camelot System® son marcas de Mixed In Key LLC. Serato™ y Serato DJ Pro™ son marcas de Serato Limited. Todas las demás marcas son propiedad de sus respectivos dueños. XfinAudio es un proyecto independiente sin afiliación a estas empresas.",

    # Labels / Guidance
    "Library: none": "Biblioteca: ninguna",
    "Choose a folder to scan metadata.": "Elija una carpeta para escanear metadata.",
    "Scan metadata before recommending a playlist.": "Escanee metadata antes de recomendar una playlist.",
    "Scan: idle": "Escaneo: inactivo",
    "Choose a folder to begin": "Elija una carpeta para comenzar",
    "Folder selected. Scan metadata to find complete Mixed In Key tracks.":
        "Carpeta seleccionada. Escanee metadata para encontrar tracks completos de Mixed In Key.",
    "Use filters/search, select a complete track, then recommend.":
        "Use filtros/búsqueda, seleccione un track completo, luego recomiende.",
    "DJ Decision Point: choose source, filters, and the track anchor.":
        "Punto de Decisión DJ: elija fuente, filtros y el track ancla.",
    "DJ Decision Point: complete missing metadata, then refresh the library.":
        "Punto de Decisión DJ: complete metadata faltante, luego refresque la biblioteca.",
    "Choose a Mixed In Key processed folder before scanning metadata.":
        "Elija una carpeta procesada por Mixed In Key antes de escanear metadata.",
    "Choose a folder before scanning": "Elija una carpeta antes de escanear",
    "Scan tracks before recommending": "Escanee tracks antes de recomendar",
    "Select at least one complete track before recommending":
        "Seleccione al menos un track completo antes de recomendar",
    "Select at least one complete track before generating Prep Copilot":
        "Seleccione al menos un track completo antes de generar Prep Copilot",

    # Scan
    "Scan progress: starting": "Progreso de escaneo: iniciando",
    "Scanning metadata": "Escaneando metadata",
    "Scan canceled; no partial results were saved": "Escaneo cancelado; no se guardaron resultados parciales",
    "Scan complete: {0} complete, {1} incomplete": "Escaneo completo: {0} completos, {1} incompletos",
    "Scan failed: {0}": "Escaneo fallido: {0}",
    "Cancel requested; waiting for current file to finish": "Cancelación solicitada; esperando que termine el archivo actual",
    "Scan delta refreshed": "Delta de escaneo refrescado",
    "Scan delta refresh failed: {0}": "Refresco de delta fallido: {0}",
    "Scan complete: {0} new, {1} updated, {2} unchanged, {3} complete, {4} incomplete":
        "Escaneo completo: {0} nuevos, {1} actualizados, {2} sin cambios, {3} completos, {4} incompletos",

    # Recommendation
    "Generating recommendation from {0} candidate track(s)": "Generando recomendación desde {0} track(s) candidato(s)",
    "Recommended {0} track(s) using {1}": "Recomendados {0} track(s) usando {1}",
    "Recommendation failed: {0}": "Recomendación fallida: {0}",
    "No recommendation is ready for review.": "No hay recomendación lista para revisar.",
    "Direct Recommend": "Recomendación Directa",
    "Generating {0} Prep Copilot variant(s)": "Generando {0} variant(es) de Prep Copilot",
    "Generated {0} Prep Copilot variant(s)": "Generados {0} variant(es) de Prep Copilot",
    "Generate and select a Prep Copilot variant before applying":
        "Genere y seleccione una variante de Prep Copilot antes de aplicar",
    "Applied Prep Copilot variant: {0}": "Variante de Prep Copilot aplicada: {0}",
    "Inspect the selected Prep Copilot variant before exporting it to Serato.":
        "Inspeccione la variante de Prep Copilot seleccionada antes de exportarla a Serato.",
    "Applied Variant: none": "Variante Aplicada: ninguna",
    "Applied Variant: {0}": "Variante Aplicada: {0}",
    "No Prep Copilot variant is currently applied.": "No hay variante de Prep Copilot aplicada actualmente.",
    "This variant will be used for Serato preview/export.": "Esta variante se usará para preview/export de Serato.",
    "Inspect the review table before exporting. Review scores and warnings before any safe export to Serato.":
        "Inspeccione la tabla de revisión antes de exportar. Revise puntajes y advertencias antes de cualquier exportación segura a Serato.",

    # Review
    "Review summary: Tracks: {0} | Transitions: {1} | Average transition score: {2:.3f} | Warnings: {3}":
        "Resumen de revisión: Tracks: {0} | Transiciones: {1} | Puntaje promedio de transición: {2:.3f} | Advertencias: {3}",
    "DJ Readiness: No recommendation ready.": "DJ Readiness: No hay recomendación lista.",
    "Blocked: do not export yet": "Bloqueado: no exportar todavía",
    "Cleared: export allowed": "Desbloqueado: exportación permitida",
    "Blocked": "Bloqueado",
    "Cleared": "Desbloqueado",

    # Export / Serato
    "Choose music folder": "Elegir carpeta de música",
    "Choose safe export folder": "Elegir carpeta de exportación segura",
    "Safe export folder must be outside the selected audio folder":
        "La carpeta de exportación segura debe estar fuera de la carpeta de audio seleccionada",
    "Safe export folder selected": "Carpeta de exportación segura seleccionada",
    "Generate a recommendation before exporting DJ readiness":
        "Genere una recomendación antes de exportar DJ readiness",
    "Choose a safe export folder before exporting DJ readiness":
        "Elija una carpeta de exportación segura antes de exportar DJ readiness",
    "Exported DJ readiness report: {0} and {1}": "Reporte de DJ readiness exportado: {0} y {1}",
    "Generate a recommendation before previewing Serato export":
        "Genere una recomendación antes de previsualizar exportación a Serato",
    "Serato not found — open Serato DJ Pro at least once to create its library folder":
        "Serato no encontrado — abra Serato DJ Pro al menos una vez para crear su carpeta de biblioteca",
    "Serato export preview: {0} | {1} track(s) | variant: {2}":
        "Preview de exportación Serato: {0} | {1} track(s) | variante: {2}",
    "Serato export preview failed: {0}": "Preview de exportación Serato fallido: {0}",
    "Resolve blocked readiness checks before exporting.": "Resuelva las verificaciones de readiness bloqueadas antes de exportar.",
    "Generate a recommendation before exporting to Serato": "Genere una recomendación antes de exportar a Serato",
    "Serato crate exported: {0}. Open Serato DJ Pro and check the crate under Subcrates.":
        "Crate de Serato exportado: {0}. Abra Serato DJ Pro y verifique el crate bajo Subcrates.",
    "Exported Serato crate: {0}": "Crate de Serato exportado: {0}",
    "Export canceled.": "Exportación cancelada.",
    "Serato metadata export failed: {0}": "Exportación de metadata a Serato fallida: {0}",
    "Exported {0} metadata crate: {1}": "Crate de metadata {0} exportado: {1}",
    "No {0} tracks are available for metadata export": "No hay tracks {0} disponibles para exportación de metadata",
    "Choose Complete or Incomplete before exporting a metadata worklist":
        "Elija Completos o Incompletos antes de exportar un worklist de metadata",
    "No tracks are missing {0} for metadata export": "No hay tracks faltando {0} para exportación de metadata",
    "Exported Missing {0} metadata crate: {1}": "Crate de metadata Missing {0} exportado: {1}",
    "Complete missing metadata in Serato, then click Scan Metadata in XfinAudio to refresh.":
        "Complete metadata faltante en Serato, luego haga clic en Escanear Metadata en XfinAudio para refrescar.",
    "Complete missing metadata in Serato, then choose the same folder and click Scan Metadata to refresh.":
        "Complete metadata faltante en Serato, luego elija la misma carpeta y haga clic en Escanear Metadata para refrescar.",
    "Build a playlist first to see export options. Exports are written to _Serato_/Subcrates/*.crate. Preview shows crate contents without writing files. Open Serato after export to verify the crate appears in Subcrates.":
        "Construya una playlist primero para ver opciones de exportación. Las exportaciones se escriben en _Serato_/Subcrates/*.crate. El preview muestra contenido del crate sin escribir archivos. Abra Serato después de exportar para verificar que el crate aparece en Subcrates.",

    # Library status
    "Library: saved": "Biblioteca: guardada",
    "Saved library loaded; no scan folder selected.": "Biblioteca guardada cargada; ninguna carpeta de escaneo seleccionada.",
    "Library: saved folder": "Biblioteca: carpeta guardada",
    "Loaded saved library: {0} complete, {1} incomplete": "Biblioteca guardada cargada: {0} completos, {1} incompletos",
    "Folder selected": "Carpeta seleccionada",
    "Could not open: {0}": "No se pudo abrir: {0}",

    # Table headers
    "Title": "Título",
    "Artist": "Artista",
    "BPM": "BPM",
    "Key": "Key",
    "Energy": "Energía",
    "Missing": "Faltante",
    "Genre": "Género",
    "Tags/Subgenre": "Tags/Subgénero",
    "Status": "Estado",
    "Path": "Ruta",
    "Order": "Orden",
    "Copilot": "Copilot",
    "Applied": "Aplicado",
    "Description": "Descripción",
    "Playlist Order": "Orden Playlist",
    "Score": "Puntaje",
    "Left Track": "Track Izquierdo",
    "Right Track": "Track Derecho",
    "Warning": "Advertencia",
    "Time": "Hora",
    "Strategy": "Estrategia",
    "Tracks": "Tracks",
    "Serato Crate": "Crate Serato",
    "Readiness JSON": "Readiness JSON",
    "Readiness CSV": "Readiness CSV",

    # Tooltips / Hints
    "Musical key in Camelot notation (e.g. 8A, 11B)": "Key musical en notación Camelot (ej. 8A, 11B)",
    "Primary genre detected by Mixed In Key": "Género principal detectado por Mixed In Key",
    "Energy level from 1-10 (Mixed In Key style)": "Nivel de energía de 1-10 (estilo Mixed In Key)",
    "Completion status: complete or incomplete": "Estado de completitud: completo o incompleto",
    "Absolute file path": "Ruta absoluta del archivo",
    "Track #{0} in playlist": "Track #{0} en playlist",
    "Track name or title": "Nombre del track o título",
    "Track artist": "Artista del track",
    "BPM: {0}": "BPM: {0}",
    "Camelot key: {0}": "Camelot key: {0}",
    "Energy level: {0}": "Nivel de energía: {0}",
    "Validation: {0}": "Validación: {0}",
    "Status: {0}": "Estado: {0}",
    "Score color: {0}": "Color de puntaje: {0}",
    "Same Camelot key — perfectly compatible": "Mismo Camelot key — perfectamente compatible",
    "Adjacent or diagonal number — harmonically compatible": "Número adyacente o diagonal — armónicamente compatible",
    "Same Camelot letter (A/B) — relative key": "Misma letra Camelot (A/B) — key relativa",
    "+2 on wheel — energy boost": "+2 en la rueda — energy boost",
    "Other Camelot move — moderate compatibility": "Otro movimiento Camelot — compatibilidad moderada",
    "Incompatible Camelot move": "Movimiento Camelot incompatible",
    "BPMs are nearly identical": "BPMs casi idénticos",
    "BPM difference is moderate": "Diferencia de BPM es moderada",
    "BPMs are far apart": "BPMs muy separados",
    "Energy jump — may feel abrupt": "Salto de energía — puede sentirse abrupto",
    "Same energy — smooth transition": "Misma energía — transición suave",
    "Different genres/tags — musical contrast": "Géneros/tags diferentes — contraste musical",
    "DJ boost rule — marked as compatible": "Regla DJ boost — marcado como compatible",
    "60% Key + 20% BPM + 15% Energy + 5% Tags": "60% Key + 20% BPM + 15% Energía + 5% Tags",

    # Build screen
    "Recommend Playlist": "Recomendar Playlist",
    "Exclude Selected": "Excluir Seleccionados",
    "Lock Selected": "Bloquear Seleccionados",
    "Clear Constraints": "Limpiar Restricciones",
    "Genre focus": "Enfoque de género",
    "Generate Prep Copilot": "Generar Prep Copilot",
    "Set Tracks": "Establecer Tracks",
    "Apply Selected Variant": "Aplicar Variante Seleccionada",
    "← Library": "← Biblioteca",
    "Review →": "Revisar →",
    "Anchor: {0}": "Ancla: {0}",
    "Select a track in the Library to set the anchor.": "Seleccione un track en la Biblioteca para establecer el ancla.",
    "{0} excluded": "{0} excluidos",
    "{0} locked": "{0} bloqueados",

    # Review screen
    "Left": "Izquierdo",
    "Right": "Derecho",
    "Tonal compatibility (Camelot). 1.0 = same key, 0.9 = adjacent or diagonal, 0.85 = relative A/B, 0.0 = incompatible":
        "Compatibilidad tonal (Camelot). 1.0 = mismo key, 0.9 = adyacente o diagonal, 0.85 = relativa A/B, 0.0 = incompatible",

    # Export screen
    "Preview Serato Export": "Preview Exportación Serato",
    "Export DJ Readiness": "Exportar DJ Readiness",
    "Export Applied Variant": "Exportar Variante Aplicada",
    "No exports yet. Build a playlist, review it, and export to Serato.":
        "Sin exportaciones todavía. Construya una playlist, revísela y exporte a Serato.",

    # Metadata screen
    "Export to Serato": "Exportar a Serato",
    "Search worklist...": "Buscar worklist...",
    "No tracks in worklist.": "No hay tracks en el worklist.",
    "No tracks match the current filter.": "Ningún track coincide con el filtro actual.",
    "Complete tracks": "Tracks completos",
    "Incomplete tracks": "Tracks incompletos",
    "Missing BPM": "Falta BPM",
    "Missing Key": "Falta Key",
    "Missing Energy": "Falta Energía",
    "Filter by status: complete or incomplete": "Filtrar por estado: completo o incompleto",
    "Filter by missing metadata field": "Filtrar por campo de metadata faltante",
    "Metadata worklist for DJ cleanup. Export missing-metadata crates to Serato.":
        "Worklist de metadata para limpieza DJ. Exporte crates de metadata faltante a Serato.",
    "{0} tracks — {1} complete, {2} incomplete": "{0} tracks — {1} completos, {2} incompletos",
    "{0} tracks — {1} missing BPM, {2} missing Key, {3} missing Energy":
        "{0} tracks — {1} falta BPM, {2} falta Key, {3} falta Energía",

    # View models
    "Active: {0}": "Activo: {0}",
    "by {0}": "por {0}",
    "Prep Copilot: {0} variant(s) | Anchor: {1}": "Prep Copilot: {0} variante(s) | Ancla: {1}",
    "Direct: {0} track(s)": "Directo: {0} track(s)",
    "No tracks selected": "Ningún track seleccionado",
    "{0} track(s) selected": "{0} track(s) seleccionados",
    "Strategy: {0}": "Estrategia: {0}",
    "Anchor: {0} | {1} track(s)": "Ancla: {0} | {1} track(s)",
    "Tracks: {0} | Duration: {1} | Avg BPM: {2:.1f}": "Tracks: {0} | Duración: {1} | BPM Prom: {2:.1f}",
    "Excluded: {0}": "Excluidos: {0}",
    "Locked: {0}": "Bloqueados: {0}",
    "Warning: {0}": "Advertencia: {0}",
    "Constraint: {0}": "Restricción: {0}",
    "Applied variant: {0}": "Variante aplicada: {0}",
    "No variant applied": "Ninguna variante aplicada",
    "Recommendation: {0} tracks": "Recomendación: {0} tracks",
    " (variant: {0})": " (variante: {0})",
    "Avg transition score: {0:.2f} ({1} transition(s), {2} warning(s))":
        "Puntaje promedio de transición: {0:.2f} ({1} transición(es), {2} advertencia(s))",
    " Readiness: {0}": " Readiness: {0}",
    "Safe export: {0}": "Exportación segura: {0}",
    "Exports are written to the _Serato_/Subcrates folder as *.crate files.":
        "Las exportaciones se escriben en la carpeta _Serato_/Subcrates como archivos *.crate.",
    "Exports are written to _Serato_/Subcrates/*.crate. Preview shows crate contents without writing files. Open Serato after export to verify the crate appears in Subcrates.":
        "Las exportaciones se escriben en _Serato_/Subcrates/*.crate. El preview muestra contenido del crate sin escribir archivos. Abra Serato después de exportar para verificar que el crate aparece en Subcrates.",
    "Build a playlist first to see export options.": "Construya una playlist primero para ver opciones de exportación.",
    "No previous crate existed.": "No existía un crate anterior.",
    " Backup: {0}": " Backup: {0}",
    "Readiness reports: {0} and {1}.": "Reportes de readiness: {0} y {1}.",
    "{0} track(s)": "{0} track(s)",
    "Export history": "Historial de exportaciones",
    "No export history.": "Sin historial de exportaciones.",

    # Rendering / Warnings
    "Camelot key": "Camelot key",
    "energy level": "nivel de energía",
    "Missing {0}": "Falta {0}",
    "Missing BPM": "Falta BPM",
    "Missing Key": "Falta Key",
    "Missing Energy": "Falta Energía",
    "Review metadata: {0} track is missing {1} metadata. Complete before recommending.":
        "Revisar metadata: el track {0} tiene falta de metadata {1}. Complete antes de recomendar.",
    "Review Mixed In Key metadata: {0} track has invalid Camelot key {1!r}. Complete before recommending.":
        "Revisar metadata de Mixed In Key: el track {0} tiene Camelot key inválido {1!r}. Complete antes de recomendar.",
    "Review Mixed In Key metadata: at least one transition has an invalid Camelot key.":
        "Revisar metadata de Mixed In Key: al menos una transición tiene un Camelot key inválido.",
    "invalid Camelot key": "Camelot key inválido",
    "Review summary: ": "Resumen de revisión: ",
    "Tracks: {0} | Transitions: {1} | Average transition score: {2:.3f} | Warnings: {3}":
        "Tracks: {0} | Transiciones: {1} | Puntaje promedio de transición: {2:.3f} | Advertencias: {3}",

    # Table populators
    "Key": "Key",
    "BPM": "BPM",
    "Energy": "Energía",
    "Tag": "Tag",
    "Final": "Final",
    "Relative major/minor (A↔B same number) — compatible": "Relativa mayor/menor (A↔B mismo número) — compatible",
    "Low harmonic compatibility — may clash": "Baja compatibilidad armónica — puede chocar",
    "Large BPM gap — mix carefully": "Gran diferencia de BPM — mezcle con cuidado",
    "Same energy level": "Mismo nivel de energía",
    "Slight energy difference": "Ligera diferencia de energía",
    "Tracks share many tags/genres": "Tracks comparten muchos tags/géneros",
    "Some tag/genre overlap": "Algo de superposición de tags/géneros",
    "Weighted average of all components": "Promedio ponderado de todos los componentes",
    "{0:g} BPM": "{0:g} BPM",
    "energy {0}": "energía {0}",
    "Recommend Playlist builds one deterministic sequence from the selected anchor. Prep Copilot compares safe, balanced, and adventurous alternatives before you choose.":
        "Recommend Playlist construye una secuencia determinística desde el ancla seleccionado. Prep Copilot compara alternativas seguras, balanceadas y aventureras antes de elegir.",
    "Exclude removes selected library tracks from generated results. Lock forces selected tracks into the candidate pool.":
        "Exclude elimina tracks seleccionados de la biblioteca de los resultados generados. Lock fuerza tracks seleccionados al pool de candidatos.",
    "{0} warning(s)": "{0} advertencia(s)",
    "no warnings": "sin advertencias",
    "{0} tracks generated. First: {1}. {2}. Review mix details before export.":
        "{0} tracks generados. Primero: {1}. {2}. Revise detalles del mix antes de exportar.",
    "Review recommendations before exporting; desktop export setup is intentionally out of scope.":
        "Revise recomendaciones antes de exportar; la configuración de exportación de escritorio está intencionalmente fuera de alcance.",
    "No safe export folder selected": "Ninguna carpeta de exportación segura seleccionada",
    "Export Readiness Report": "Exportar Reporte de Readiness",
    "← Review": "← Revisar",
    "Variant: Safe": "Variante: Segura",
    "Variant: Balanced": "Variante: Balanceada",
    "Variant: Adventurous": "Variante: Aventurera",
    "{0} tracks → {1}": "{0} tracks → {1}",
    "{0} tracks": "{0} tracks",
    "Variant: {0}": "Variante: {0}",
    "No safe folder set": "Ninguna carpeta segura establecida",
    "Preview shows the planned crate contents without writing any files.":
        "El preview muestra el contenido planeado del crate sin escribir archivos.",
    "Search songs": "Buscar canciones",
    "⚙ Settings": "⚙ Configuración",
    "Build Playlist →": "Construir Playlist →",
    "Scanning… {0:,} tracks": "Escaneando… {0:,} tracks",
    "Scanning…": "Escaneando…",
    "saved library": "biblioteca guardada",
    "{0} tracks · {1}/{0} complete · {2}": "{0} tracks · {1}/{0} completos · {2}",
    "Ready to scan · {0}": "Listo para escanear · {0}",
    "{0} track selected": "{0} track seleccionado",
    "{0} tracks selected": "{0} tracks seleccionados",
    "Selected row starts the playlist; multiple selected rows set the opening order. Up to 25 candidates are used for interactive speed. Choose a strategy, then click Recommend Playlist.":
        "La fila seleccionada inicia la playlist; múltiples filas seleccionadas establecen el orden de apertura. Hasta 25 candidatos se usan para velocidad interactiva. Elija una estrategia, luego haga clic en Recomendar Playlist.",
    "Safe export folder: {0}": "Carpeta de exportación segura: {0}",
    "Showing saved library from the app database. Choose a folder to re-scan or update metadata.":
        "Mostrando biblioteca guardada de la base de datos de la app. Elija una carpeta para re-escanear o actualizar metadata.",
    "Saved library loaded: {0}": "Biblioteca guardada cargada: {0}",
    "Saved library loaded. Click Scan Metadata to refresh metadata from the last folder.":
        "Biblioteca guardada cargada. Haga clic en Escanear Metadata para refrescar metadata de la última carpeta.",
    "Review recommendations before exporting. Serato export is enabled only after a recommendation is ready.":
        "Revise recomendaciones antes de exportar. La exportación a Serato se habilita solo después de que una recomendación esté lista.",
    "Serato export preview: {0} | Variant: {1} | Tracks: {2} | Will write: {3} | Readiness: {4}":
        "Preview de exportación Serato: {0} | Variante: {1} | Tracks: {2} | Escribirá: {3} | Readiness: {4}",
    "Serato export preview: {0}": "Preview de exportación Serato: {0}",
    "Serato export failed: {0}": "Exportación a Serato fallida: {0}",
    " No previous crate existed.": " No existía un crate anterior.",
    " Readiness reports: {0} and {1}.": " Reportes de readiness: {0} y {1}.",
    "Metadata worklist exported: {0}. Complete missing metadata in Serato, then choose the same folder and click Scan Metadata to refresh XfinAudio.":
        "Worklist de metadata exportado: {0}. Complete metadata faltante en Serato, luego elija la misma carpeta y haga clic en Escanear Metadata para refrescar XfinAudio.",
    "Metadata worklist exported: {0}. Complete missing metadata in Serato, then click Scan Metadata in XfinAudio to refresh.":
        "Worklist de metadata exportado: {0}. Complete metadata faltante en Serato, luego haga clic en Escanear Metadata en XfinAudio para refrescar.",
    "No tracks found. Choose another folder or re-scan after adding supported audio files.":
        "No se encontraron tracks. Elija otra carpeta o re-escanee después de agregar archivos de audio soportados.",
    "Refresh complete: {0} incomplete → {1} incomplete; {2} fixed":
        "Refresco completo: {0} incompletos → {1} incompletos; {2} arreglados",
    "Scan progress: {0}/{1} - {2}": "Progreso de escaneo: {0}/{1} - {2}",
    "Scan your library first to see metadata status": "Escanee su biblioteca primero para ver el estado de metadata",
    "{0} tracks scanned — {1} complete, {2} incomplete": "{0} tracks escaneados — {1} completos, {2} incompletos",
    "The worklist shows tracks missing BPM, Key, or Energy. These fields are required for harmonic mixing recommendations.":
        "El worklist muestra tracks faltando BPM, Key o Energía. Estos campos son requeridos para recomendaciones de harmonic mixing.",
    "Fix missing tags in an external tag editor, then return to XfinAudio.":
        "Arregle tags faltantes en un editor de tags externo, luego regrese a XfinAudio.",
    "Refresh the library scan to pick up corrected metadata.":
        "Refresque el escaneo de biblioteca para capturar metadata corregida.",
    "Review metadata: {0} track is missing Mixed In Key {1} metadata. Re-scan or update tags before relying on this transition.":
        "Revisar metadata: el track {0} tiene falta de metadata {1} de Mixed In Key. Re-escanee o actualice tags antes de confiar en esta transición.",
    "Review Mixed In Key metadata: {0} track has invalid Camelot key {1!r}. Expected values look like 8A or 11B.":
        "Revisar metadata de Mixed In Key: el track {0} tiene Camelot key inválido {1!r}. Los valores esperados se ven como 8A o 11B.",
    "Review note: {0}": "Nota de revisión: {0}",
    "Remove from Playlist": "Remover de Playlist",
    "💡 Each row shows how two consecutive tracks blend. Green = excellent, Yellow = acceptable, Red = risky. Hover over any score for details.":
        "💡 Cada fila muestra cómo se mezclan dos tracks consecutivos. Verde = excelente, Amarillo = aceptable, Rojo = riesgoso. Pase el mouse sobre cualquier puntaje para detalles.",
    "← Build": "← Construir",
    "Export →": "Exportar →",
    "No playlist generated": "Ninguna playlist generada",
    "Needs review before export": "Necesita revisión antes de exportar",
    "Ready to export": "Listo para exportar",

    # Settings dialog
    "Settings…": "Configuración…",
    "Concept: Freddy Molina": "Concepto: Freddy Molina",
    "Version 1.0": "Versión 1.0",
    "Language Changed": "Idioma Cambiado",
    "Please restart XfinAudio for the language change to take effect.":
        "Por favor reinicie XfinAudio para que el cambio de idioma tenga efecto.",
    "Settings": "Configuración",
    "UI Language": "Idioma de la UI",
    "Language:": "Idioma:",
    "Auto (system default)": "Auto (predeterminado del sistema)",
    "Export Settings": "Configuración de Exportación",
    "Safe export folder:": "Carpeta de exportación segura:",
    "Choose…": "Elegir…",
    "Library Settings": "Configuración de Biblioteca",
    "Last scan folder:": "Última carpeta escaneada:",
    "None": "Ninguna",
    "Choose safe export folder": "Elegir carpeta de exportación segura",
    "Duration": "Duración",
    "XfinAudio is a metadata-driven DJ playlist assistant that helps DJs build harmonically coherent playlists from existing track metadata.":
        "XfinAudio es un asistente de playlists DJ basado en metadata que ayuda a DJs a construir playlists armónicamente coherentes a partir de metadata de tracks existentes.",
    "All rights reserved.": "Todos los derechos reservados.",
    "Developed by Freddy Molina.": "Desarrollado por Freddy Molina.",
    "This software is open-source and distributed under the GNU General Public License v3.0.":
        "Este software es open-source y se distribuye bajo la GNU General Public License v3.0.",
}


def main() -> int:
    tree = ET.parse(TS_PATH)
    root = tree.getroot()

    for message in root.iter("message"):
        source_elem = message.find("source")
        trans_elem = message.find("translation")
        if source_elem is None or trans_elem is None:
            continue
        source_text = source_elem.text or ""
        if source_text in TRANSLATIONS:
            trans_elem.text = TRANSLATIONS[source_text]
            trans_elem.attrib.pop("type", None)

    # Preserve XML declaration and formatting
    tree.write(TS_PATH, encoding="utf-8", xml_declaration=True)
    print(f"Updated {TS_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
