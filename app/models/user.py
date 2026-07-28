"""
Inicialização do ORM (SQLAlchemy) para o projeto Flask.
Importa configurações do banco de dados do config.py.
"""
from flask_login import UserMixin

from app.config import db


class User(db.Model, UserMixin):
    
    def save(self):
        db.session.add(self)
        db.session.commit()

    __tablename__ = 'JDT_USER_DETAILS'
    id = db.Column(db.String(100), primary_key=True, unique=True)
    registration = db.Column(db.String(100), unique=True)
    name = db.Column(db.String(100), unique=True)
    companyEmail = db.Column(db.String(100), unique=True)
    groupEmail = db.Column(db.String(100), unique=True)
    shift = db.Column(db.String(100), unique=True)
    areaId = db.Column(db.String(100), unique=True)
    role = db.Column(db.String(100), unique=True)
    position = db.Column(db.String(100), unique=True)
    department = db.Column(db.String(100), unique=True)
    companyName = db.Column(db.String(100), unique=True)
    managerId = db.Column(db.String(100), unique=True)
    admin = db.Column(db.String(100), unique=True)
    active = db.Column(db.String(100), unique=True)
    generic = db.Column(db.String(100), unique=True)
    temp = db.Column(db.String(100), unique=True)