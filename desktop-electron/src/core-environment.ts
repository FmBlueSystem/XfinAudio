/** The new runtime only uses a credential source selected explicitly in its own UI. */
export function coreEnvironment(parent:NodeJS.ProcessEnv):NodeJS.ProcessEnv {
  const env={...parent,PYTHONUNBUFFERED:'1',PYTHONDONTWRITEBYTECODE:'1'} as NodeJS.ProcessEnv;
  for(const key of ['PYTHONHOME','PYTHONPATH','NAN_API_KEY','NAN_API_BASE','NAN_MODEL','XFINAUDIO_AI_ENABLED','XFINAUDIO_AI_ENV_FILE'])delete env[key];
  return env;
}
