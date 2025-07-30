FROM python:3.10-slim

# Instala o LibreOffice headless
RUN apt-get update && apt-get install -y \
    libreoffice \
    libreoffice-writer \
    python3-pip \
    && apt-get clean

WORKDIR /app

COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8501

CMD ["streamlit", "run", "main.py", "--server.address=0.0.0.0"]
