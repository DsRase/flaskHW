from flask import Flask, abort, request
from src.db import engine, User
from os import getenv
import redis
import json
from sqlalchemy.orm import Session
import logging

r = redis.Redis(host=getenv("REDIS_HOST"), port=6379, db=0)

def get_cached(key):
    data = r.get(key)
    if data:
        return json.loads(data)
    else:
        return False

app = Flask(__name__)

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