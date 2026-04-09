#  Agentic — FPGA-Accelerated Smart Agriculture System

An intelligent, agentic agricultural monitoring and advisory system that combines **Zynq-7000 FPGA hardware acceleration**, **Groq LLM inference**, **real-time sensor fusion**, and **WhatsApp-based farmer Q&A** — all served through a modern React dashboard and FastAPI backend.

---

##  Features

- **FPGA-Accelerated Sensor Fusion** — ZC706 Zynq-7000 FPGA processes soil moisture, temperature, humidity, and light data via custom HLS/RTL IP cores
- **FPGA Rain Prediction** — Hardware-accelerated rainfall prediction using temperature, humidity, pressure, and wind speed
- **LLM-Powered Farm Advisor** — Groq-hosted LLaMA-3 provides contextual farming recommendations based on live sensor data
- **WhatsApp Q&A** — Farmers can ask questions via WhatsApp (Twilio) and receive AI-driven, sensor-backed answers
- **Real-Time Dashboard** — React + TypeScript frontend with live sensor readings, FPGA status, AI advisor, and weather insights
- **MQTT Sensor Ingestion** — ESP32/LoRa sensor data streamed via MQTT and stored in SQLite
- **Autonomous Alerts** — Configurable alerts via Twilio WhatsApp with cooldown and deduplication

---

##  Project Structure

```
agentic/
├── app.py                      # FastAPI backend — all API endpoints
├── agricultural_qa.py          # Agricultural Q&A module (LLM + sensor context)
├── fpga_dual_bridge.py         # FPGA UART bridge (ZC706 dual accelerator)
├── unified_zc706_bridge.py     # Unified ZC706 bridge implementation
├── decision_engine_dual.py     # Dual decision engine logic
├── llm_accelerator_agent.py    # LLM accelerator agent
├── weather_workflow_llm_first.py # Weather workflow (LLM-first approach)
├── tools.py                    # Tool functions for LangGraph agents
├── sensor_endpoints.py         # Sensor data API endpoints
├── sensor_models.py            # Pydantic sensor data models
├── mqtt_sensor_simulator.py    # MQTT sensor data simulator
├── mqtt_monitor.py             # MQTT broker monitor
├── esp32_mqtt_simulator.py     # ESP32 MQTT simulator
├── esp32_sensor_simulator.py   # ESP32 sensor simulator
├── send_sensor_data.py         # Sensor data sender utility
├── init_db.py                  # Database initialization (PostgreSQL)
├── init_db_sqlite.py           # Database initialization (SQLite)
├── schema_sqlite.sql           # SQLite database schema
├── requirements.txt            # Python dependencies
├── .env                        # Environment configuration
│
├── frontend/                   # React + TypeScript dashboard (Vite)
│   ├── src/
│   │   ├── pages/              # Dashboard, Advisor, Accelerator pages
│   │   ├── components/         # UI components (panels, charts, maps)
│   │   ├── hooks/              # Custom React hooks
│   │   └── lib/                # Utility libraries
│   ├── package.json
│   └── vite.config.ts
│
├── hls/                        # Vivado HLS source files
│   ├── sensor_fusion.cpp       # Sensor fusion HLS implementation
│   ├── sensor_fusion.h         # Sensor fusion header
│   ├── sensor_fusion_tb.cpp    # HLS testbench
│   └── rain_predictor/         # Rain predictor HLS
│
├── rtl/                        # Verilog RTL source files
│   ├── sensor_fusion.v         # Sensor fusion RTL
│   ├── sensor_fusion_axi.v     # AXI-wrapped sensor fusion
│   ├── rain_predictor.v        # Rain predictor RTL
│   ├── rain_predictor_axi.v    # AXI-wrapped rain predictor
│   └── sensor_fusion_pkg.vh    # RTL package definitions
│
└── ip_repo/                    # Vivado IP repository
    ├── component.xml           # IP-XACT component descriptor
    └── src/                    # IP core sources
```

---

##  Tech Stack

| Layer | Technology |
|-------|-----------|
| **Backend** | Python, FastAPI, Uvicorn |
| **Frontend** | React, TypeScript, Vite, Tailwind CSS, shadcn/ui |
| **LLM** | Groq (LLaMA-3), LangChain, LangGraph |
| **FPGA** | Xilinx Zynq-7000 (ZC706), Vivado HLS, Verilog |
| **Database** | SQLite (dev), PostgreSQL (prod) |
| **Messaging** | Twilio WhatsApp Business API |
| **IoT** | ESP32, MQTT |

---

##  Getting Started

### Prerequisites

- **Python 3.10+**
- **Node.js 18+** and **npm**
- **Groq API Key** — [Get free key](https://console.groq.com/keys)
- *(Optional)* Xilinx ZC706 FPGA board connected via UART (COM4)
- *(Optional)* Twilio account for WhatsApp integration

### 1. Clone & Install Backend

```bash
git clone https://github.com/your-repo/agentic.git
cd agentic

# Install Python dependencies
pip install -r requirements.txt
```

### 2. Configure Environment

Edit the `.env` file in the project root:

```env
# Database
DATABASE_URL=sqlite:///C:/path/to/agentic/sensor_data.db

# Groq LLM
GROQ_API_KEY=gsk_your_api_key_here

# FPGA (set to false if no hardware)
FPGA_ENABLED=true
FPGA_PORT=COM4

# Twilio WhatsApp (optional)
TWILIO_ACCOUNT_SID=your_sid
TWILIO_AUTH_TOKEN=your_token
TWILIO_WHATSAPP_NUMBER=+14155238886
TWILIO_ALERT_RECIPIENT=+91xxxxxxxxxx

# Server
PORT=8000
```

### 3. Initialize Database

```bash
python init_db_sqlite.py
```

### 4. Start Backend

```bash
python app.py
```

The API server starts at `http://localhost:8000`.

### 5. Start Frontend

```bash
cd frontend
npm install
npm run dev
```

The dashboard opens at `http://localhost:5173`.

---

##  API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | System status |
| `GET` | `/health` | Health check |
| `GET` | `/api/sensor/latest/{station_id}` | Latest sensor readings |
| `POST` | `/api/sensor/lora` | Receive LoRa sensor data |
| `POST` | `/api/fpga/sensor-fusion` | FPGA sensor fusion |
| `POST` | `/api/fpga/rain-predict` | FPGA rain prediction |
| `POST` | `/api/fpga/combined-analysis` | Combined FPGA analysis |
| `GET` | `/api/fpga/status` | FPGA accelerator status |
| `POST` | `/api/advisor/insights` | AI farming advisor |
| `POST` | `/api/weather/insight` | Weather insight (LLM) |
| `POST` | `/api/chat` | General chat endpoint |
| `POST` | `/api/agricultural-qa` | Agricultural Q&A |
| `POST` | `/webhook/whatsapp` | WhatsApp webhook |
| `POST` | `/webhook/whatsapp/farm-qa` | WhatsApp farm Q&A |

---

##  WhatsApp Integration

1. Create a [Twilio](https://www.twilio.com/) account and enable WhatsApp
2. Add your Twilio credentials to `.env`
3. Set webhook URL in Twilio Console to: `https://your-domain.com/webhook/whatsapp/farm-qa`
4. Farmers can message questions like:
   - *"How is my soil moisture?"*
   - *"Should I irrigate today?"*
   - *"Will it rain?"*
   - *"Why is my plant stressed?"*

---

##  FPGA Hardware Setup

The system uses a **Xilinx ZC706 (Zynq-7000)** board with two custom accelerators:

1. **Sensor Fusion Accelerator** — Fuses soil, temperature, humidity, and light data into actionable crop health scores
2. **Rain Predictor Accelerator** — Predicts rainfall probability from environmental inputs

### Connection
- Board connected via **UART** (default: `COM4`)
- Set `FPGA_ENABLED=true` in `.env`
- If no hardware is available, the system falls back to a software mock automatically

### Building IP Cores (Vivado)
```bash
cd hls
make csim     # Run C simulation
make synth    # Run HLS synthesis
```

---

##  Running Sensor Simulators

If you don't have physical ESP32 hardware, use the simulators:

```bash
# MQTT sensor simulator (requires MQTT broker like Mosquitto)
python mqtt_sensor_simulator.py

# ESP32 MQTT simulator
python esp32_mqtt_simulator.py

# Simple sensor data sender
python send_sensor_data.py
```

---

##  Architecture

```
ESP32 + LoRa Sensors
        │
        ▼
   MQTT Broker ──────► mqtt_monitor.py
        │
        ▼
   FastAPI Backend (app.py)
   ├── Sensor Endpoints
   ├── FPGA Bridge (UART) ◄──► ZC706 FPGA
   │   ├── Sensor Fusion IP
   │   └── Rain Predictor IP
   ├── Groq LLM (LangChain/LangGraph)
   │   ├── Farm Advisor Agent
   │   ├── Weather Workflow
   │   └── Agricultural QA
   ├── Twilio WhatsApp Webhook
   └── SQLite Database
        │
        ▼
   React Dashboard (frontend/)
   ├── Live Sensor Panels
   ├── FPGA Accelerator View
   ├── AI Farm Advisor
   └── Weather Insights
```

---

This project is developed for academic and research purposes.
