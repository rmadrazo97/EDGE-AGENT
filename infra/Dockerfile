FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml .
COPY src/ src/
COPY configs/ configs/

RUN pip install --no-cache-dir -e .

CMD ["python3", "-m", "agents.trader.agent"]
