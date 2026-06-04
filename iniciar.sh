#!/usr/bin/env bash
# Script de arranque rapido para Linux y Mac.
# Crea un entorno virtual, instala dependencias y levanta el servidor.

set -e

cd "$(dirname "$0")"

# Crear entorno virtual si no existe
if [ ! -d "venv" ]; then
  echo "Creando entorno virtual..."
  python3 -m venv venv
fi

# Activar e instalar dependencias
source venv/bin/activate
pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt

echo ""
echo "Servidor iniciando en http://localhost:8000"
echo "Pulsa Ctrl+C para detenerlo."
echo ""

cd backend
uvicorn main:app --reload --port 8000
