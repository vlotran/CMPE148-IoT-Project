# CMPE148 IoT Smart Home Simulator (MQTT vs CoAP)

This project simulates a small smart-home IoT network using **Mininet** and compares two lightweight application-layer protocols:

- **MQTT** (publish/subscribe via Mosquitto broker)
- **CoAP** (UDP request/response via a CoAP server)

Sensors periodically generate telemetry. The gateway collects messages, logs them to CSV, and captures traffic using tcpdump so the experiments are reproducible and comparable.

---

## Team Members
| Name | Email | 
|------|-------|
| Vy Tran | vylophuong.tran@sjsu.edu | 
| Diana Bader | diana.bader@sjsu.edu | 
| Mangsagar Bath | mangsagar.bath@sjsu.edu | 
| Canhui Huang | canhui.huang@sjsu.edu | 


---

## Requirements

### OS / Environment
- Linux machine (Ubuntu recommended) with Mininet support
- Root access (`sudo`) for Mininet/tcpdump

### System Packages (NOT in requirements.txt)
Install these via `apt` (or your distro package manager):
- `mininet`
- `mosquitto`
- `tcpdump`
- Python 3.10+ recommended

Ubuntu example:
```bash
sudo apt update
sudo apt install -y mininet mosquitto tcpdump
```

### Python Packages (requirements.txt)
Install via `pip`:
- `paho-mqtt`
- `aiocoap`
- `pandas`
- `matplotlib`

---

## Repo Structure

```
CMPE148-IoT-Project/
  configs/
    mosquitto.conf
  src/
    topology.py
    run_experiment.py
    mqtt_sensor.py
    mqtt_logger.py
    coap_sensor.py
    coap_server.py
  notebooks/
    02_analyze_results.ipynb
  results/
    run_*/                # generated experiment outputs
  requirements.txt        # Python deps only (pip)
```

---

## Setup

### 1) Create a virtual environment (recommended)
```bash
cd CMPE148-IoT-Project
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
```

### 2) Install Python dependencies
```bash
pip install -r requirements.txt
```

---

## Running Experiments (Terminal)

Always run from repo root:
```bash
cd CMPE148-IoT-Project
```

### MQTT run
```bash
sudo python3 src/run_experiment.py --protocol mqtt --duration 30 --delay 5ms
```

### CoAP run
```bash
sudo python3 src/run_experiment.py --protocol coap --duration 30 --delay 5ms
```

### View generated runs
```bash
ls -lt results | head
```

Each run writes outputs under:
```
results/run_<timestamp>/
  meta.json
  logs/
  mqtt.csv + mqtt.pcap     (MQTT run)
  coap.csv + coap.pcap     (CoAP run)
```

---

## Analysis / Visualization (Notebook)

Start Jupyter from repo root:
```bash
source .venv/bin/activate
jupyter lab
```
### Headless / SSH note
If you are on a headless Linux machine (no GUI) or connecting via SSH, run:

```bash
jupyter lab --no-browser --ip=0.0.0.0 --port=8888
```

Open:
- `notebooks/02_analyze_results.ipynb`

This notebook:
- finds the latest MQTT run and latest CoAP run
- prints summary metrics (avg msg/sec, latency mean/p50/p95)
- plots message rate over time and latency distributions
- optionally compares pcap overhead (bytes/msg)

### If you get `ModuleNotFoundError` in the notebook
Ensure your notebook kernel uses `.venv`:

```bash
source .venv/bin/activate
pip install ipykernel
python -m ipykernel install --user --name cmpe148-venv --display-name "CMPE148 (.venv)"
```

Then in Jupyter: **Kernel → Change Kernel → CMPE148 (.venv)**.

---

## Troubleshooting

### Mininet cleanup (if a run crashes)
```bash
sudo mn -c
sudo pkill -f mosquitto || true
sudo pkill -f tcpdump || true
```

### Sudo prompts inside notebooks
Recommended: run experiments in the terminal (above), and use the notebook only for analysis.
```
---

## Current Implementation Progress

### Completed
- Mininet smart-home topology implemented (gateway + temp sensors)
- Reproducible experiment runner (`src/run_experiment.py`) for MQTT and CoAP
- Unified CSV logging format for fair protocol comparison (includes `seq` + `latency_ms`)
- Packet capture (pcap) collection for protocol overhead analysis
- Analysis notebook (`notebooks/02_analyze_results.ipynb`) for metrics + plots + MQTT vs CoAP comparison

### Current Status
- MQTT and CoAP runs are working end-to-end
- Baseline comparison (2 sensors, 5ms link delay) is producing latency and throughput results
- Next focus: broaden experiments (load, delay/loss, topology variations) and strengthen evaluation

---

## Next Experiments / Extensions

### 1) Scalability (load testing)
Vary number of sensors (e.g., 2 → 5 → 10 → 20) and compare:
- throughput (msg/sec)
- latency (mean / p50 / p95)
- delivery reliability (missing `seq` numbers)

### 2) Network impairment tests
Increase link delay and add loss to simulate constrained networks:
- delay: 0ms, 10ms, 50ms, 100ms
- loss: 0%, 1%, 3%, 5%

Compare how MQTT vs CoAP behaves under degraded conditions.

### 3) MQTT QoS comparison (MQTT-only)
Test QoS levels (0 vs 1 vs 2) and measure:
- latency impact
- reliability improvements
- overhead increase (pcap bytes/packets)

### 4) Protocol overhead analysis (pcap-based)
Compute:
- packets per delivered message
- bytes per delivered message
- compare MQTT vs CoAP overhead under the same sending rate

### 5) Topology variations
Add a second topology for comparison, e.g.:
- star topology (current baseline)
- two-hop topology (sensors → intermediate switch/router → gateway)

Measure how multi-hop affects performance for MQTT vs CoAP.

---
