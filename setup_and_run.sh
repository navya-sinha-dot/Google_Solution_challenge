#!/bin/bash
set -e

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

# ── Load nvm so npm/node are on PATH in non-interactive shells ─────────────────
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && source "$NVM_DIR/nvm.sh"
nvm use --lts

echo "========================================="
echo " AMD Hack — Setup & Run Script"
echo "========================================="

# ── 1. Python check ───────────────────────────────────────────────────────────
echo ""
echo "[1/6] Checking Python..."
if command -v python3 &>/dev/null; then
    PYTHON=python3
elif command -v python &>/dev/null; then
    PYTHON=python
else
    echo "ERROR: Python not found. Install Python 3.10+ first."
    exit 1
fi
$PYTHON --version

# ── 2. Node / npm check ───────────────────────────────────────────────────────
echo ""
echo "[2/6] Checking Node.js / npm..."
if ! command -v node &>/dev/null; then
    echo "ERROR: Node.js not found."
    echo "  Install via: brew install node   (macOS)"
    echo "  Or:          https://nodejs.org"
    exit 1
fi
if ! command -v npm &>/dev/null; then
    echo "ERROR: npm not found. Re-install Node.js from https://nodejs.org"
    exit 1
fi
echo "Node $(node --version)  |  npm $(npm --version)"

# ── 3. Docker + local Postgres ────────────────────────────────────────────────
echo ""
echo "[3/6] Starting local PostgreSQL via Docker..."
if ! command -v docker &>/dev/null; then
    echo "ERROR: Docker not found. Install Docker Desktop from https://docker.com"
    exit 1
fi
if ! docker info &>/dev/null; then
    echo "ERROR: Docker daemon is not running. Start Docker Desktop and try again."
    exit 1
fi

docker compose up -d db

echo "  Waiting for Postgres to be ready..."
MAX_WAIT=30
WAITED=0
until docker compose exec -T db pg_isready -U amd_user -d amd_hack -q 2>/dev/null; do
    if [ $WAITED -ge $MAX_WAIT ]; then
        echo "ERROR: Postgres did not become ready in ${MAX_WAIT}s."
        exit 1
    fi
    sleep 1
    WAITED=$((WAITED + 1))
done
echo "  PostgreSQL is ready (waited ${WAITED}s)."

# ── 4. Python virtual environment & dependencies ──────────────────────────────
echo ""
echo "[4/6] Installing Python dependencies..."
if [ ! -d "$PROJECT_DIR/.venv" ]; then
    $PYTHON -m venv "$PROJECT_DIR/.venv"
    echo "  Created virtual environment at .venv/"
fi
source "$PROJECT_DIR/.venv/bin/activate"
pip install -q --upgrade pip
pip install -r requirements.txt
echo "  Python dependencies installed."

# ── 5. Frontend npm dependencies ─────────────────────────────────────────────
echo ""
echo "[5/6] Installing frontend dependencies..."
cd "$PROJECT_DIR/frontend"
npm install --no-fund --no-audit
echo "  Frontend dependencies installed."
cd "$PROJECT_DIR"

# ── 6. Database schema init ───────────────────────────────────────────────────
echo ""
echo "[6/6] Initialising database schema..."
$PYTHON "$PROJECT_DIR/init_db.py"

# ── Launch ────────────────────────────────────────────────────────────────────
cleanup() {
    echo ""
    echo "Stopping app servers (Docker DB keeps running)..."
    kill 0
}
trap cleanup SIGINT SIGTERM EXIT

echo ""
echo "========================================="
echo " Starting servers..."
echo "  Backend  →  http://localhost:8000"
echo "  Frontend →  http://localhost:5173"
echo "  Database →  localhost:5432  (Docker)"
echo "  Press Ctrl+C to stop app servers."
echo "  To also stop DB: docker compose down"
echo "========================================="

# Backend (venv already activated)
$PYTHON "$PROJECT_DIR/app.py" &

# Frontend
cd "$PROJECT_DIR/frontend"
npm run dev &

wait
