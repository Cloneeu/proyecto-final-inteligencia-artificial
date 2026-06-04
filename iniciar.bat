@echo off
REM Script de arranque rapido para Windows.
REM Crea un entorno virtual, instala dependencias y levanta el servidor.

cd /d "%~dp0"

if not exist venv (
  echo Creando entorno virtual...
  python -m venv venv
)

call venv\Scripts\activate
pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt

echo.
echo Servidor iniciando en http://localhost:8000
echo Pulsa Ctrl+C para detenerlo.
echo.

cd backend
uvicorn main:app --reload --port 8000
