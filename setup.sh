#!/usr/bin/env bash
# FloodIQ — one-shot local setup
#
# Usage:
#   ./setup.sh
#
# Sets up both backend (venv + deps + trained model) and frontend
# (npm install) so the team can get from a fresh clone to a running
# system with one command. Run uvicorn/npm run dev in separate
# terminals after this completes (see printed instructions at the end).

set -e

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "=================================================="
echo " FloodIQ Setup"
echo "=================================================="

echo ""
echo "--- Backend ---"
cd "$ROOT_DIR/backend"

if [ ! -d "venv" ]; then
  echo "Creating Python virtual environment..."
  python3 -m venv venv
fi

source venv/bin/activate
echo "Installing backend dependencies (this may take a few minutes)..."
pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt

if [ ! -f "ml/model.pkl" ]; then
  echo "Training ML model (first run, ~2 minutes)..."
  python -m ml.train_model
else
  echo "ML model already trained (ml/model.pkl exists). Skipping."
fi

deactivate
cd "$ROOT_DIR"

echo ""
echo "--- Frontend ---"
cd "$ROOT_DIR/frontend"

if [ ! -f ".env" ]; then
  cp .env.example .env
  echo "Created frontend/.env from template."
fi

echo "Installing frontend dependencies..."
npm install --silent

cd "$ROOT_DIR"

echo ""
echo "=================================================="
echo " Setup complete!"
echo "=================================================="
echo ""
echo "To run FloodIQ, open two terminals:"
echo ""
echo "  Terminal 1 (backend):"
echo "    cd backend && source venv/bin/activate && uvicorn main:app --reload --port 8000"
echo ""
echo "  Terminal 2 (frontend):"
echo "    cd frontend && npm run dev"
echo ""
echo "  Then open http://localhost:5173"
echo ""
