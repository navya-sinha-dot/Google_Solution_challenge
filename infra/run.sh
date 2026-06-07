#!/usr/bin/env bash
# =============================================================
# SkyView Smart Agriculture — Local Run Script
# Usage: ./run.sh
# Runs the FastAPI backend locally (without Docker).
# Requires: Python 3.11+, optional PostgreSQL or uses SQLite.
# =============================================================

set -euo pipefail

# ── Colors ────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_ROOT"

echo -e "${BLUE}=============================================${NC}"
echo -e "${BLUE}🌾 SkyView Smart Agriculture Backend v2.0${NC}"
echo -e "${BLUE}=============================================${NC}"

# ── .env check ────────────────────────────────────────────────
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}⚠️  No .env found — creating from .env.example${NC}"
    if [ -f ".env.example" ]; then
        cp .env.example .env
        echo -e "${GREEN}✅ .env created. Edit it with your credentials before production use.${NC}"
    else
        echo -e "${RED}❌ .env.example not found. Cannot continue.${NC}"
        exit 1
    fi
fi

# Load env vars (skip comments and blank lines)
set -o allexport
# shellcheck disable=SC1090
source <(grep -v '^#' .env | grep -v '^$')
set +o allexport
echo -e "${GREEN}✅ Environment loaded${NC}"

# ── Python check ──────────────────────────────────────────────
if ! command -v python3 &>/dev/null; then
    echo -e "${RED}❌ Python 3 not found. Install Python 3.11+.${NC}"
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
echo -e "${GREEN}✅ Python ${PYTHON_VERSION}${NC}"

# ── Virtual environment ───────────────────────────────────────
VENV_DIR="${PROJECT_ROOT}/venv"
if [ ! -d "$VENV_DIR" ]; then
    echo -e "${BLUE}Creating virtual environment...${NC}"
    python3 -m venv "$VENV_DIR"
fi

# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"
echo -e "${GREEN}✅ Virtual environment active${NC}"

# ── Dependencies ──────────────────────────────────────────────
echo -e "${BLUE}Installing/checking dependencies...${NC}"
pip install --quiet -r infra/requirements.txt
echo -e "${GREEN}✅ Dependencies installed${NC}"

# ── Database schema init ──────────────────────────────────────
echo -e "${BLUE}Initialising database schema...${NC}"
python3 - <<'PYEOF'
import sys
sys.path.insert(0, ".")
try:
    from skyview.data.db import init_db
    from skyview.data.schema import create_all
    init_db()
    create_all()
    print("  ✅ Schema ready")
except Exception as e:
    print(f"  ⚠️  Schema init warning (continuing): {e}")
PYEOF

# ── MQTT bridge (optional background service) ─────────────────
MQTT_PID=""
if [ "${ENABLE_MQTT:-True}" = "True" ]; then
    if python3 -c "import paho.mqtt.client" 2>/dev/null; then
        echo -e "${BLUE}Starting MQTT bridge in background...${NC}"
        python3 -m skyview.ingestion.mqtt_bridge &
        MQTT_PID=$!
        echo -e "${GREEN}✅ MQTT bridge started (PID: ${MQTT_PID})${NC}"
    else
        echo -e "${YELLOW}⚠️  paho-mqtt not installed; skipping MQTT bridge${NC}"
    fi
fi

# ── Cleanup on exit ───────────────────────────────────────────
cleanup() {
    echo -e "\n${BLUE}Shutting down...${NC}"
    [ -n "$MQTT_PID" ] && kill "$MQTT_PID" 2>/dev/null || true
    echo -e "${GREEN}Goodbye 🌾${NC}"
}
trap cleanup INT TERM EXIT

# ── Start API server ──────────────────────────────────────────
HOST="${API_HOST:-0.0.0.0}"
PORT="${API_PORT:-8000}"
WORKERS="${API_WORKERS:-1}"
RELOAD_FLAG=""
[ "${DEBUG:-False}" = "True" ] && RELOAD_FLAG="--reload"

echo ""
echo -e "${GREEN}=============================================${NC}"
echo -e "${GREEN}🚀 Starting SkyView API on http://${HOST}:${PORT}${NC}"
echo -e "${GREEN}   Docs: http://localhost:${PORT}/docs${NC}"
echo -e "${GREEN}   Admin: http://localhost:${PORT}/admin/tables${NC}"
echo -e "${GREEN}=============================================${NC}"
echo ""

# shellcheck disable=SC2086
uvicorn skyview.main:app \
    --host "$HOST" \
    --port "$PORT" \
    --workers "$WORKERS" \
    $RELOAD_FLAG