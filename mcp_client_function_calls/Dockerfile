FROM python:3.11-slim

WORKDIR /app

RUN pip install openai requests pyyaml psycopg2-binary

COPY . .

CMD ["python", "mcp_client.py"]