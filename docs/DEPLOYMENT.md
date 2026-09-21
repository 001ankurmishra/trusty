# TrustForge Deployment Guide

This guide covers deploying TrustForge on an air-gapped (zero-network) machine using systemd.

## Prerequisites

- Target OS: Linux (Ubuntu/Debian) or macOS. (Instructions assume Linux).
- CPU-only execution with 16GB RAM minimum.
- Python 3.10+ installed on the host.

## 1. Preparing the Offline Payload

On a machine WITH internet access:
1. Clone the repository.
2. Download Ollama for Linux: `curl -L https://ollama.com/download/ollama-linux-amd64.tgz -o ollama.tgz`
3. Download the model weights: Start Ollama locally and run `ollama pull qwen2.5:3b-instruct`. Then, tar the `.ollama` directory: `tar -czvf ollama-models.tar.gz ~/.ollama`
4. Create the Python virtual environment and download packages:
   ```bash
   cd sova/backend
   python3 -m venv venv
   source venv/bin/activate
   pip install --download wheelhouse -r requirements.txt
   ```
5. Build the frontend:
   ```bash
   cd ../frontend
   npm install
   npm run build
   ```
6. Package everything onto a USB drive.

## 2. Air-Gapped Installation

On the target air-gapped machine:
1. Copy the payload from the USB drive to `/opt/trustforge`.
2. Extract Ollama: `sudo tar -C /usr -xzf ollama.tgz`
3. Extract model weights: `tar -xzvf ollama-models.tar.gz -C ~/`
4. Install Python dependencies:
   ```bash
   cd /opt/trustforge/sova/backend
   python3 -m venv venv
   source venv/bin/activate
   pip install --no-index --find-links=wheelhouse -r requirements.txt
   ```

## 3. Systemd Services

Create `/etc/systemd/system/trustforge-backend.service`:
```ini
[Unit]
Description=TrustForge Backend
After=network.target ollama.service

[Service]
User=appuser
WorkingDirectory=/opt/trustforge/sova/backend
Environment="PATH=/opt/trustforge/sova/backend/venv/bin:$PATH"
ExecStart=/opt/trustforge/sova/backend/venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable --now trustforge-backend
```

Serve the frontend via a reverse proxy (e.g. Nginx) pointing to `/opt/trustforge/sova/frontend/dist` and proxy `/api` to `127.0.0.1:8000`.
