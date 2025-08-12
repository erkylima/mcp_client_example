FROM python:3.11-slim

WORKDIR /app

COPY api_mock_server.py .

RUN pip install flask

EXPOSE 5000

CMD ["python", "api_mock_server.py"]
