FROM python:3.11-slim

WORKDIR /app

COPY . /app

CMD ["sh", "-c", "python -u server.py & python -u technology/1956-commons/infrastructure/commons-observer-agent.py"]