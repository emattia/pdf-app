#!/bin/sh
if [ -f /run/secrets/openai_api_key ]; then
  export OPENAI_API_KEY=$(cat /run/secrets/openai_api_key)
  echo "[DEBUG] OpenAI API key set from secret"
else
  echo "[ERROR] Secret file not found at /run/secrets/openai_api_key"
fi

exec "$@"
