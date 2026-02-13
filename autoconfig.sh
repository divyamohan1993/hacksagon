#!/usr/bin/env bash
# ============================================================================
#  ECO-LENS AUTOCONFIG — Idempotent Setup, Key Rotation & Launch
#  Run on any blank VM (Ubuntu/Debian/RHEL/macOS) or re-run to rotate keys.
#  Usage:  chmod +x autoconfig.sh && ./autoconfig.sh
# ============================================================================
set -euo pipefail

# ---- Configuration ----
BACKEND_PORT=40881
FRONTEND_PORT=40882
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
NODE_MIN_MAJOR=18
LOGS_DIR="$PROJECT_DIR/logs"
BACKEND_DIR="$PROJECT_DIR/backend"
FRONTEND_DIR="$PROJECT_DIR/frontend"
ENV_FILE="$PROJECT_DIR/.env"
BACKEND_ENV="$BACKEND_DIR/.env"
PID_BACKEND="$LOGS_DIR/backend.pid"
PID_FRONTEND="$LOGS_DIR/frontend.pid"

# ---- Colors ----
R='\033[0;31m' G='\033[0;32m' Y='\033[1;33m' B='\033[0;34m' C='\033[0;36m' NC='\033[0m'
info()  { echo -e "${G}[INFO]${NC}  $1"; }
warn()  { echo -e "${Y}[WARN]${NC}  $1"; }
err()   { echo -e "${R}[ERROR]${NC} $1"; }
step()  { echo -e "${B}[STEP]${NC}  $1"; }
header(){ echo -e "${C}$1${NC}"; }

# ============================================================================
# STEP 1 — System Dependencies
# ============================================================================
install_system_deps() {
    step "1/7  Installing system dependencies..."

    if command -v apt-get &>/dev/null; then
        sudo apt-get update -qq
        sudo apt-get install -y -qq \
            python3 python3-venv python3-pip python3-dev \
            curl wget git openssl build-essential ca-certificates lsof 2>/dev/null

        if ! command -v node &>/dev/null || \
           [ "$(node -v | tr -d 'v' | cut -d. -f1)" -lt "$NODE_MIN_MAJOR" ]; then
            info "Installing Node.js 20 via NodeSource..."
            curl -fsSL "https://deb.nodesource.com/setup_20.x" | sudo -E bash - 2>/dev/null
            sudo apt-get install -y -qq nodejs 2>/dev/null
        fi

    elif command -v yum &>/dev/null; then
        sudo yum install -y python3 python3-pip python3-devel \
            curl wget git openssl gcc-c++ make lsof 2>/dev/null
        if ! command -v node &>/dev/null; then
            curl -fsSL "https://rpm.nodesource.com/setup_20.x" | sudo bash - 2>/dev/null
            sudo yum install -y nodejs 2>/dev/null
        fi

    elif command -v pacman &>/dev/null; then
        sudo pacman -Sy --noconfirm python python-pip nodejs npm \
            curl wget git openssl base-devel lsof 2>/dev/null

    elif command -v brew &>/dev/null; then
        brew install python@3.11 node@20 openssl 2>/dev/null || true
    else
        err "Unsupported package manager. Install Python 3.9+ and Node 18+ manually."
        exit 1
    fi

    # Verify
    python3 --version >/dev/null 2>&1 || { err "Python 3 not found after install"; exit 1; }
    node    --version >/dev/null 2>&1 || { err "Node.js not found after install"; exit 1; }
    npm     --version >/dev/null 2>&1 || { err "npm not found after install"; exit 1; }
    openssl version   >/dev/null 2>&1 || { err "openssl not found after install"; exit 1; }

    info "Python $(python3 --version 2>&1 | awk '{print $2}') | Node $(node -v) | npm $(npm -v)"
}

# ============================================================================
# STEP 2 — Stop any running Eco-Lens processes
# ============================================================================
stop_existing() {
    step "2/7  Stopping existing Eco-Lens processes..."

    for PIDFILE in "$PID_BACKEND" "$PID_FRONTEND"; do
        if [ -f "$PIDFILE" ]; then
            PID=$(cat "$PIDFILE" 2>/dev/null || true)
            if [ -n "$PID" ] && kill -0 "$PID" 2>/dev/null; then
                kill "$PID" 2>/dev/null || true
                info "Sent SIGTERM to PID $PID"
                sleep 1
                kill -0 "$PID" 2>/dev/null && kill -9 "$PID" 2>/dev/null || true
            fi
            rm -f "$PIDFILE"
        fi
    done

    # Free ports if occupied by stale processes
    for PORT in $BACKEND_PORT $FRONTEND_PORT; do
        PIDS=$(lsof -ti :"$PORT" 2>/dev/null || true)
        if [ -n "$PIDS" ]; then
            echo "$PIDS" | xargs kill -9 2>/dev/null || true
            info "Force-freed port $PORT"
        fi
    done

    sleep 2
    info "Cleanup complete"
}

# ============================================================================
# STEP 3 — Generate / Rotate Cryptographic Keys & Produce .env
# ============================================================================
manage_env() {
    step "3/7  Managing environment & rotating security keys..."

    # ---- Preserve user-supplied values from existing .env ----
    local PREV_OWM="" PREV_CAM1="" PREV_CAM2="" PREV_CAM3="" PREV_SIM="true"

    if [ -f "$ENV_FILE" ]; then
        warn "Existing .env detected — rotating ALL security keys"
        BACKUP="$ENV_FILE.backup.$(date +%Y%m%d_%H%M%S)"
        cp "$ENV_FILE" "$BACKUP"
        info "Backup → $BACKUP"

        # Extract user values (preserved across rotations)
        PREV_OWM=$(grep  '^OPENWEATHERMAP_API_KEY=' "$ENV_FILE" 2>/dev/null | cut -d= -f2- || true)
        PREV_CAM1=$(grep '^CAMERA_FEED_URL_1='      "$ENV_FILE" 2>/dev/null | cut -d= -f2- || true)
        PREV_CAM2=$(grep '^CAMERA_FEED_URL_2='      "$ENV_FILE" 2>/dev/null | cut -d= -f2- || true)
        PREV_CAM3=$(grep '^CAMERA_FEED_URL_3='      "$ENV_FILE" 2>/dev/null | cut -d= -f2- || true)
        PREV_SIM=$(grep  '^SIMULATION_MODE='         "$ENV_FILE" 2>/dev/null | cut -d= -f2- || echo "true")
    fi

    # ---- Generate fresh cryptographic material ----
    local API_SECRET_KEY ENCRYPTION_KEY JWT_SECRET_KEY SESSION_SECRET
    local DB_ENCRYPTION_KEY INTERNAL_AUTH_TOKEN CORS_SIGNING_KEY WS_AUTH_TOKEN

    API_SECRET_KEY=$(openssl rand -hex 32)
    ENCRYPTION_KEY=$(openssl rand -hex 32)
    JWT_SECRET_KEY=$(openssl rand -hex 64)
    SESSION_SECRET=$(openssl rand -hex 32)
    DB_ENCRYPTION_KEY=$(openssl rand -hex 32)
    INTERNAL_AUTH_TOKEN=$(openssl rand -hex 48)
    CORS_SIGNING_KEY=$(openssl rand -hex 16)
    WS_AUTH_TOKEN=$(openssl rand -hex 32)

    # ---- Write .env ----
    cat > "$ENV_FILE" <<ENVFILE
# ============================================
# ECO-LENS — Auto-Generated Configuration
# Generated: $(date -u +"%Y-%m-%dT%H:%M:%SZ")
# Re-run autoconfig.sh to rotate security keys
# ============================================

# ---- Enterprise Security Keys (Auto-Rotated) ----
API_SECRET_KEY=${API_SECRET_KEY}
ENCRYPTION_KEY=${ENCRYPTION_KEY}
JWT_SECRET_KEY=${JWT_SECRET_KEY}
SESSION_SECRET=${SESSION_SECRET}
DB_ENCRYPTION_KEY=${DB_ENCRYPTION_KEY}
INTERNAL_AUTH_TOKEN=${INTERNAL_AUTH_TOKEN}
CORS_SIGNING_KEY=${CORS_SIGNING_KEY}
WS_AUTH_TOKEN=${WS_AUTH_TOKEN}

# ---- Server ----
HOST=0.0.0.0
PORT=${BACKEND_PORT}
FRONTEND_URL=http://localhost:${FRONTEND_PORT}

# ---- OpenWeatherMap API ----
OPENWEATHERMAP_API_KEY=${PREV_OWM:-your_openweathermap_api_key_here}

# ---- Mode ----
SIMULATION_MODE=${PREV_SIM}

# ---- Camera Feed URLs ----
CAMERA_FEED_URL_1=${PREV_CAM1}
CAMERA_FEED_URL_2=${PREV_CAM2}
CAMERA_FEED_URL_3=${PREV_CAM3}

# ---- Database ----
DATABASE_URL=sqlite:///./ecolens.db

# ---- Processing ----
FRAME_INTERVAL=5
SENSOR_UPDATE_INTERVAL=5
WEATHER_UPDATE_INTERVAL=300

# ---- Map ----
MAP_CENTER_LAT=40.7580
MAP_CENTER_LNG=-73.9855

# ---- Frontend ----
NEXT_PUBLIC_API_URL=http://localhost:${BACKEND_PORT}
NEXT_PUBLIC_WS_URL=ws://localhost:${BACKEND_PORT}/ws
ENVFILE

    chmod 600 "$ENV_FILE"

    # Backend needs its own copy (pydantic-settings loads from cwd)
    cp "$ENV_FILE" "$BACKEND_ENV"
    chmod 600 "$BACKEND_ENV"

    info "8 security keys generated (rotated)"
    info "  API_SECRET  = ${API_SECRET_KEY:0:12}..."
    info "  ENCRYPTION  = ${ENCRYPTION_KEY:0:12}..."
    info "  JWT_SECRET  = ${JWT_SECRET_KEY:0:12}..."
    info "  File perms  = 600 (owner-only read/write)"
}

# ============================================================================
# STEP 4 — Backend: venv + dependencies
# ============================================================================
setup_backend() {
    step "4/7  Setting up Python backend..."

    cd "$BACKEND_DIR"

    if [ ! -d "venv" ]; then
        python3 -m venv venv
        info "Created virtual environment"
    fi

    # shellcheck disable=SC1091
    source venv/bin/activate

    pip install --upgrade pip setuptools wheel -q 2>/dev/null
    pip install -r requirements.txt -q 2>/dev/null

    deactivate
    info "Backend dependencies installed/updated"
}

# ============================================================================
# STEP 5 — Frontend: npm install
# ============================================================================
setup_frontend() {
    step "5/7  Setting up Next.js frontend..."

    cd "$FRONTEND_DIR"
    npm install --silent 2>/dev/null
    info "Frontend dependencies installed/updated"
}

# ============================================================================
# STEP 6 — Open firewall ports (idempotent)
# ============================================================================
configure_firewall() {
    step "6/7  Configuring firewall rules..."

    if command -v ufw &>/dev/null; then
        sudo ufw allow "$BACKEND_PORT"/tcp  comment "EcoLens Backend"  2>/dev/null || true
        sudo ufw allow "$FRONTEND_PORT"/tcp comment "EcoLens Frontend" 2>/dev/null || true
        info "UFW rules added for ports $BACKEND_PORT, $FRONTEND_PORT"
    elif command -v firewall-cmd &>/dev/null; then
        sudo firewall-cmd --permanent --add-port="$BACKEND_PORT"/tcp 2>/dev/null || true
        sudo firewall-cmd --permanent --add-port="$FRONTEND_PORT"/tcp 2>/dev/null || true
        sudo firewall-cmd --reload 2>/dev/null || true
        info "firewalld rules added"
    else
        info "No firewall manager detected — skipping (ports $BACKEND_PORT, $FRONTEND_PORT)"
    fi
}

# ============================================================================
# STEP 7 — Launch services
# ============================================================================
launch_services() {
    step "7/7  Launching Eco-Lens services..."

    mkdir -p "$LOGS_DIR"

    # ---- Backend (FastAPI + Uvicorn) ----
    cd "$BACKEND_DIR"
    # shellcheck disable=SC1091
    source venv/bin/activate

    nohup python -m uvicorn main:app \
        --host 0.0.0.0 \
        --port "$BACKEND_PORT" \
        --log-level info \
        > "$LOGS_DIR/backend.log" 2>&1 &
    local B_PID=$!
    echo "$B_PID" > "$PID_BACKEND"

    deactivate

    # ---- Frontend (Next.js dev server) ----
    cd "$FRONTEND_DIR"

    NEXT_PUBLIC_API_URL="http://localhost:$BACKEND_PORT" \
    NEXT_PUBLIC_WS_URL="ws://localhost:$BACKEND_PORT/ws" \
    PORT="$FRONTEND_PORT" \
    nohup npx next dev -p "$FRONTEND_PORT" \
        > "$LOGS_DIR/frontend.log" 2>&1 &
    local F_PID=$!
    echo "$F_PID" > "$PID_FRONTEND"

    info "Backend  started  PID=$B_PID  port=$BACKEND_PORT"
    info "Frontend started  PID=$F_PID  port=$FRONTEND_PORT"

    # ---- Health-check loop ----
    echo ""
    info "Waiting for backend to respond..."
    local ATTEMPTS=0 MAX=30 BACKEND_OK=false

    while [ $ATTEMPTS -lt $MAX ]; do
        ATTEMPTS=$((ATTEMPTS + 1))
        if curl -sf "http://localhost:$BACKEND_PORT/api/health" >/dev/null 2>&1; then
            BACKEND_OK=true
            break
        fi
        sleep 1
    done

    if $BACKEND_OK; then
        info "Backend health-check: PASSED"
    else
        warn "Backend still starting — check $LOGS_DIR/backend.log"
    fi
}

# ============================================================================
# MAIN
# ============================================================================
main() {
    header "
 =====================================================
    ECO-LENS  AUTOCONFIG  v1.0
    Virtual Air Quality Matrix
    Idempotent Setup  |  Key Rotation  |  Launch
 =====================================================
"

    install_system_deps
    stop_existing
    manage_env
    setup_backend
    setup_frontend
    configure_firewall
    launch_services

    cd "$PROJECT_DIR"

    header "
 =====================================================
           ECO-LENS IS RUNNING
 =====================================================

  Dashboard :  http://localhost:${FRONTEND_PORT}
  API       :  http://localhost:${BACKEND_PORT}
  API Docs  :  http://localhost:${BACKEND_PORT}/docs
  WebSocket :  ws://localhost:${BACKEND_PORT}/ws

  Logs      :  ${LOGS_DIR}/
  Config    :  ${ENV_FILE}

  Re-run this script to rotate all security keys.
 =====================================================
"
}

main "$@"
