/** The new runtime only uses a credential source selected explicitly in its own UI. */
export function coreEnvironment(parent:NodeJS.ProcessEnv):NodeJS.ProcessEnv {
  const env={...parent,PYTHONUNBUFFERED:'1',PYTHONDONTWRITEBYTECODE:'1'} as NodeJS.ProcessEnv;
  for(const key of ['PYTHONHOME','PYTHONPATH','NAN_API_KEY','NAN_API_BASE','NAN_MODEL','XFINAUDIO_AI_ENABLED','XFINAUDIO_AI_ENV_FILE'])delete env[key];
  // The chat diagnostic log is the DJ's own choice, so the environment made when the app
  // started is the only source of the switch; anything but the documented value is dropped
  // and the core keeps its promise that the conversation is never written to disk.
  if(parent.XFINAUDIO_CHAT_LOG==='1')env.XFINAUDIO_CHAT_LOG='1';else delete env.XFINAUDIO_CHAT_LOG;
  return env;
}
