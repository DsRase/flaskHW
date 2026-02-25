from flask import Flask, abort, request, Response
from src.db import engine, User
from os import getenv
import redis
import json
from sqlalchemy.orm import Session
import logging
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from time import time

r = redis.Redis(host=getenv("REDIS_HOST"), port=6379, db=0)

def get_cached(key):
    data = r.get(key)
    if data:
        return json.loads(data)
    else:
        return False

app = Flask(__name__)

# metric's objects
http_requests_total = Counter(
    'http_requests_total', 'Total HTTP requests',
    ['method', 'endpoint', 'http_status']
)

http_4xx_requests_total = Coutner(
    'http_4xx_requests_total', 'Total 4xx HTTP requests',
    ['method', 'endpoint', 'http_status']
)

http_5xx_requests_total = Coutner(
    'http_5xx_requests_total', 'Total 5xx HTTP requests',
    ['method', 'endpoint', 'http_status']
)

http_request_duration_seconds = Histogram(
    'http_request_duration_seconds', 'HTTP request latency in seconds',
    ['endpoint']
)

class GetMetricsMiddleware:
    def __init__(self, app):
        self.app = app

    def __call__(self, environ, start_response):
        method = environ.get('REQUEST_METHOD')
        endpoint = environ.get('PATH_INFO')
        status_code = None

        def custom_start_response(status, headers, exc_info=None):
            nonlocal status_code
            status_code = status.split()[0]
            return start_response(status, headers, exc_info)

        request_time = time()
        response = self.app(environ, start_response)
        request_time = time() - request_time

        http_request_duration_seconds.labels(endpoint).observe(duration)

        http_requests_total.labels(
            method,
            endpoint,
            status_code
        ).inc()

        match status_code[0]:
            case '4':
                http_4xx_requests_total.labels(
                    method,
                    endpoint,
                    status_code
                ).inc()
            case '5':
                http_5xx_requests_total.labels(
                    method,
                    endpoint,
                    status_code
                ).inc()

        return response

app.wsgi_app = GetMetricsMiddleware(app.wsgi_app)

@app.route('/health')
def health_check():
    return {"status": "ok"}

# CRUD
@app.route('/users', methods=["GET"])
def get_users():
    """
    Возвращает список всех пользователей.
    """
    key = "users:all"
    cache = get_cached(key)

    if cache:
        return cache

    with Session(bind=engine) as s:
        users = s.query(User).all()

        users_list = [{"id": u.id, "username": u.username, "description": u.description} for u in users]
    
    r.setex(key, 300, json.dumps(users_list))

    return users_list

@app.route('/users/<username>', methods=["GET"])
def get_user(username: str):
    """
    Возвращает информацию о конкретном пользователе.
    """
    key = f"users:{username}"
    cache = get_cached(key)

    if cache:
        return cache

    with Session(bind=engine, expire_on_commit=False) as s:
        user = s.query(User).filter_by(username=username).first()

        if not user:
            abort(404)

    data = {"id": user.id, "username": user.username, "description": user.description}

    r.setex(key, 300, json.dumps(data))
    
    return data

@app.route('/users', methods=["POST"])
def add_user():
    """
    Добавляет пользователя.
    """
    user_data = request.get_json()

    username = user_data.get("username")
    description = user_data.get("description")

    if not user_data or not username or not description:
        abort(400)

    with Session(bind=engine, expire_on_commit=False) as s:
        old_user = s.query(User).filter_by(username=username).first()

        if old_user:
            abort(400) # user is already here

        user = User(username=username, description=description)

        s.add(user)
        s.commit()
    
    return {"id": user.id, "username": user.username, "description": user.description}

@app.route('/users', methods=["PUT"])
def update_user():
    """
    Обновляет данные пользователя.
    """
    user_data = request.get_json()

    user_id = user_data.get("id")
    username = user_data.get("username")
    description = user_data.get("description")

    if not user_data or not user_id or not username or not description:
        abort(400)

    with Session(bind=engine, expire_on_commit=False) as s:
        user = s.query(User).get(user_id)

        if not user:
            abort(404)
        
        user.username = username
        user.description = description

        s.commit()
    
    return {"id": user.id, "username": user.username, "description": user.description}

@app.route('/users/<username>', methods=["DELETE"])
def delete_user(username):
    """
    Удаляет пользователя.
    """
    with Session(bind=engine) as s:
        user = s.query(User).filter_by(username=username).first()

        if not user:
            abort(404)

        s.delete(user)
        s.commit()
    
    return {"status": "ok"}

@app.route('/metrics')
def metrics():
    return Response(generate_latest(), mimetype=CONTENT_TYPE_LATEST)