const messages:Record<string,string>={
  dirty_saved_draft:'Guarda o descarta los borradores antes de eliminar una playlist guardada. Tus cambios se conservan.',
  profiles_unavailable:'No se pudieron completar los perfiles locales. Los metadatos siguen disponibles; puedes volver a intentarlo.',
  invalid_ai_response:'La respuesta no cumple los límites locales. No se ha aplicado ninguna propuesta.',
  stale_ai:'El contexto cambió. Prepara otra vista previa y revisa el consentimiento.',
  ai_request_failed:'No se pudo completar la consulta. Los datos ya enviados no se pueden recuperar.',
  ai_context_too_large:'Reduce la selección antes de consultar la asistencia IA.',
  ai_context_unavailable:'Vuelve a abrir la pantalla o selección de origen para consultar la asistencia.',
  ai_disabled:'La asistencia IA está desactivada. Revisa sus ajustes.',
  ai_unconfigured:'Selecciona una fuente de credenciales desde IA opcional.',
  ai_credentials_unavailable:'La fuente de credenciales no está disponible. Revisa su selección.',
  stale_credential:'La fuente de credenciales cambió. Actualiza los ajustes antes de continuar.',
  dirty_draft:'Hay borradores sin guardar. Revisa el editor, las preferencias, la cohesión espectral, los controles de preparación y los ajustes de sonoridad e IA. Guarda o descarta los cambios pendientes antes de analizar sonoridad. Tus borradores se conservan.',
  stale_loudness:'Las pistas o los ajustes cambiaron. Actualiza el estado de sonoridad y prepara otra vista previa.',
  loudness_unavailable:'El motor de sonoridad no está disponible. Revisa su estado antes de continuar.',
  loudness_disabled:'La sonoridad está desactivada. Revisa y guarda los ajustes antes de analizar.',
  loudness_failed:'No se pudo confirmar el resultado de sonoridad. Conserva las copias de seguridad y revisa el estado antes de repetir.',
  stale_settings:'Las preferencias cambiaron. Tu borrador se conserva; descarta los cambios y actualiza antes de guardar.',
  settings_unavailable:'No se pudieron cargar o guardar las preferencias. Revisa los ajustes y vuelve a intentarlo; no se han activado servicios adicionales.',
  live_not_ready:'La guía necesita una selección completamente lista, sin avisos ni bloqueos. Revisa los metadatos y prepara otra selección.',
  stale_live:'La selección o el paso de la guía cambió. Actualiza la sesión o vuelve a abrir una selección lista.',
  invalid_live_choice:'Elige una de las sugerencias que siguen disponibles en la guía actual.',

  export_too_large:'Esta exportación admite hasta 500 referencias de pistas. Divide la selección antes de continuar.',
  stale_source:'La selección cambió. Prepara una nueva vista previa antes de exportar.',
  stale_destination:'La carpeta o el crate cambiaron. Revisa el destino y prepara una nueva vista previa.',
  stale_preview:'La vista previa ya no está disponible. Prepara una nueva antes de confirmar.',
  export_limit:'Se alcanzó el límite de sesiones de exportación. Reinicia XfinAudio para continuar.',
  confirmation_required:'Revisa la vista previa y confirma la exportación en el diálogo del sistema.',
  export_failed:'No se pudo verificar la exportación. Revisa el destino y cualquier copia de seguridad o recuperación antes de volver a intentarlo.',

  stale_edit:'La playlist cambió. Tu borrador se conserva; descarta los cambios para recargar la versión guardada.',
  stale_review:'Esta selección ya no está vigente. Genera y revisa una nueva antes de guardar.',
  stale_plan:'Las alternativas ya no están vigentes. Vuelve a generar la selección.',
  stale_export:'La selección o la carpeta cambiaron. Prepara una nueva vista previa antes de exportar.',
  blocked_export:'La selección tiene problemas que impiden exportarla. Revisa los avisos y corrige los datos indicados.',
  invalid_destination:'Selecciona una carpeta _Serato_ válida que contenga Subcrates.',
  invalid_export_name:'Revisa el nombre del crate: usa un nombre corto, sin barras ni caracteres de control.',
  invalid_params:'Revisa los datos de la operación y sus límites antes de intentarlo de nuevo.',
  invalid_edit:'No se puede aplicar esta propuesta. Revisa los metadatos de las pistas y los límites del borrador.',
  busy:'Hay otra operación en curso. Espera a que termine antes de continuar.',
  not_found:'No se encuentra este elemento. Actualiza la biblioteca o vuelve a abrir la playlist.',
  core_stopped:'El servicio local dejó de responder. Reinicia XfinAudio para volver a conectar.',
  cancelled:'La operación se canceló. Puedes volver a intentarlo cuando quieras.',
  invalid_source:'La selección no está disponible para esta exportación. Vuelve a abrirla y revisar sus pistas.',
  invalid_preview:'La vista previa ya no está disponible. Prepara una nueva antes de confirmar.',
  invalid_track:'No se puede abrir esta pista. Comprueba que el archivo siga disponible.',
  insufficient_tracks:'Necesitas al menos dos pistas válidas para preparar una selección.',
  blocked_review:'La selección tiene bloqueos pendientes. Revisa los avisos antes de guardar.',
};
export function errorCode(error:unknown):string|null {
  const direct=typeof error==='object'&&error!==null?(error as {code?:unknown}).code:undefined;
  if(typeof direct==='string'&&/^[a-z_]{1,40}$/.test(direct))return direct;
  const message=error instanceof Error?error.message:typeof error==='string'?error:'';
  return /\[([a-z_]{1,40})\]/.exec(message)?.[1]??null;
}
export function userErrorMessage(error:unknown):string {
  return messages[errorCode(error)??'']??'No se pudo completar la operación. Actualiza la información y vuelve a intentarlo.';
}
