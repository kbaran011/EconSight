FROM python:3.12-slim

WORKDIR /app

# WeasyPrint requires Pango, Cairo, Harfbuzz, fonts
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpango-1.0-0 libpangoft2-1.0-0 libgdk-pixbuf-xlib-2.0-0 \
    libffi-dev libcairo2 libharfbuzz0b \
    fontconfig fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml .
COPY src/ src/
COPY sql/ sql/

RUN pip install --no-cache-dir .

EXPOSE 8000

CMD ["uvicorn", "econsight.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
