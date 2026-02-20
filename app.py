from flask import Flask, abort, request
from src.db import engine, User
from sqlalchemy.orm import Session

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
    with Session(bind=engine) as s:
        users = s.query(User).all()

        users_list = [{"id": u.id, "username": u.username, "description": u.description} for u in users]
    
    return users_list

@app.route('/users/<username>', methods=["GET"])
def get_user(username: str):
    """
    Возвращает информацию о конкретном пользователе.
    """
    with Session(bind=engine) as s:
        user = s.query(User).filter_by(username=username).first()

        if not user:
            abort(404)
    
    return user

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

    with Session(bind=engine) as s:
        user = User(username=username, description=description)

        s.add(user)
        s.commit()
    
    return user

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

    with Session(bind=engine) as s:
        user = s.query.get(user_id)

        if not user:
            abort(404)
        
        user.username = username
        user.description = description

        s.commit()
    
    return user

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
    
    return user