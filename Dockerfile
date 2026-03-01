FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .

RUN apt-get update && apt-get install -y \
    nginx \
    gcc \
    g++ \
    python3-dev \
    build-essential \
    libc6-dev \
    libxml2-dev \
    libxslt1-dev \
    zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

RUN pip install -r requirements.txt uwsgi

COPY . .

COPY uwsgi.ini /etc/uwsgi.ini
COPY nginx/nginx.conf /etc/nginx/nginx.conf

RUN mkdir -p /tmp && chown www-data:www-data /tmp

CMD ["sh", "-c", "service nginx start && uwsgi --ini /etc/uwsgi.ini"]