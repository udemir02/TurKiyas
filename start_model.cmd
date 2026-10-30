@echo off
cd /d "%~dp0"
set "OLLAMA_HOST=127.0.0.1:11434"
set "OLLAMA_NO_CLOUD=1"
if exist "%~dp0.tools\ollama\ollama.exe" (
  set "OLLAMA_MODELS=%~dp0.tools\models"
  "%~dp0.tools\ollama\ollama.exe" serve
) else (
  ollama serve
)
