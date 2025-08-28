from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.sql import func

db = SQLAlchemy()

class Worker(db.Model):
    __tablename__ = "workers"
    id = db.Column(db.Integer, primary_key=True)             # ID
    name = db.Column(db.String(120), nullable=False)         # 名字
    company = db.Column(db.String(120), nullable=True)       # 公司
    commission = db.Column(db.Float, default=0.0)            # 佣金
    expense = db.Column(db.Float, default=0.0)               # 开销
    created_at = db.Column(db.DateTime, server_default=func.now())  # 创建时间(自动)
