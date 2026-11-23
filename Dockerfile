FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY agent.py api.py store.py policies.json ./
COPY agent_tools ./agent_tools
COPY web ./web
ENV DATA_DIR=/data AGENT_MODE=ollama
EXPOSE 8000
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"]

