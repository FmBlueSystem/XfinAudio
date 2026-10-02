import test from 'node:test';
import assert from 'node:assert/strict';
import {errorCode,userErrorMessage} from '../renderer/errors.ts';
test('Electron transport wrappers retain machine recovery codes but never appear in user text',()=>{
 const error=new Error("Error invoking remote method 'xfin:action': Error: [stale_edit] The saved playlist changed /Users/private/music");
 assert.equal(errorCode(error),'stale_edit');
 const message=userErrorMessage(error);assert.match(message,/playlist.*cambió/i);assert.match(message,/borrador/);assert.doesNotMatch(message,/xfin:action|stale_edit|Error invoking|\/Users|The saved/);
});
test('known failures have actionable Spanish text and unknown details stay private',()=>{
 for(const code of ['invalid_params','invalid_edit','stale_review','stale_plan','stale_export','blocked_export','busy','not_found','core_stopped','cancelled']) {
  const error=Object.assign(new Error('technical private details'),{code});
  assert.equal(errorCode(error),code);assert.doesNotMatch(userErrorMessage(error),/technical|private|\[[a-z_]+\]/);assert.ok(userErrorMessage(error).length>15);
 }
 assert.equal(userErrorMessage(new Error('ENOENT /secret/path token=private')),'No se pudo completar la operación. Actualiza la información y vuelve a intentarlo.');
});
test('export conflicts and limits explain the safe next step without backend details',()=>{
 for(const [code,expected] of [['stale_source',/selección.*cambió/],['stale_destination',/carpeta.*crate.*cambi/],['stale_preview',/vista previa/],['export_limit',/Reinicia/],['confirmation_required',/confirma/],['export_failed',/copia.*seguridad/]])assert.match(userErrorMessage(new Error(`[${code}] raw private detail`)),expected);
});
test('Live failures explain readiness, stale source and eligible-choice recovery',()=>{
 for(const [code,expected] of [['live_not_ready',/lista.*sin avisos/],['stale_live',/guía.*cambió/],['invalid_live_choice',/sugerencias.*disponibles/]])assert.match(userErrorMessage(new Error(`[${code}] technical detail`)),expected);
});
