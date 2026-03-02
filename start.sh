#!/bin/bash
set -e

# Start FastAPI API server on internal port 8081.
python -m uvicorn api.main:app --host 127.0.0.1 --port 8081 &

# Start Streamlit dashboard on internal port 8501.
python -m streamlit run dashboard/streamlit_app.py \
    --server.port 8501 \
    --server.address 127.0.0.1 \
    --server.headless true \
    --browser.gatherUsageStats false &

# Run nginx reverse proxy in foreground on port 8080 (exposed to Fly.io).
exec nginx -c /app/nginx.conf -g 'daemon off;'
