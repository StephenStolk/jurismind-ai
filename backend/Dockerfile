FROM python:3.11-slim

# System deps for OCR + spaCy + build tools
RUN apt-get update && apt-get install -y \
    g++ \
    build-essential \
    tesseract-ocr \
    tesseract-ocr-hin \
    tesseract-ocr-eng \
    poppler-utils \
    libglib2.0-0 \
    libgomp1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir --default-timeout=1000 -r requirements.txt


# Install spaCy transformer support + OpenNyAI model
RUN pip install --no-cache-dir spacy-transformers
RUN pip install --no-cache-dir --no-deps \
    https://huggingface.co/opennyaiorg/en_legal_ner_trf/resolve/main/en_legal_ner_trf-any-py3-none-any.whl

# Copy app
COPY . .

# Create dirs
RUN mkdir -p uploads chroma_db

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]