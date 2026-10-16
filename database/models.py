from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db=SQLAlchemy()

class Listing(db.Model):
    __tablename__="listings"
    id=db.Column(db.Integer, primary_key=True)
    title=db.Column(db.String(500), nullable=False)
    product_type=db.Column(db.String(100), default="")
    brand=db.Column(db.String(200), default="")
    model=db.Column(db.String(200), default="")
    input_data=db.Column(db.Text, default="{}")
    output_data=db.Column(db.Text, default="{}")
    created_at=db.Column(db.DateTime, default=datetime.utcnow)

class DataPacket(db.Model):
    __tablename__="data_packets"
    id=db.Column(db.Integer,primary_key=True)
    model=db.Column(db.String(200),index=True,nullable=False)
    product_name=db.Column(db.String(500),default="")
    input_data=db.Column(db.Text,default="{}")
    packet_text=db.Column(db.Text,nullable=False)
    updated_at=db.Column(db.DateTime,default=datetime.utcnow)
