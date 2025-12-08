FROM python:3.11-slim

WORKDIR /usr/src/backend

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

# Run the dev server with auto-reload
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
