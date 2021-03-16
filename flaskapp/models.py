from flaskapp import db
from datetime import datetime
from sqlalchemy.dialects.postgresql import JSON
import json


class shortReport(db.Model):
    __tablename__ = 'shortReport'
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False)
    stocks = db.Column(JSON, nullable=False)

    def __init__(self, date, stocks):
        self.date = date
        self.stocks = stocks

    def __repr__(self):
        return '<Short record {}>'.format(self.date)