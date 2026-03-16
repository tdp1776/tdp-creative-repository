FROM python:3.11-slim

WORKDIR /app
COPY . /app

CMD ["python", "technology/1956-commons/infrastructure/commons-observer-agent.py"]