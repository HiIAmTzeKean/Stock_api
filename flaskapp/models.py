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

class stockTicker(db.Model):
    __tablename__ = 'stockTicker'
    __table_args__ = (db.UniqueConstraint('name', 'ticker'),)
    name = db.Column(db.String, nullable=False)
    ticker = db.Column(db.String, nullable=False, primary_key=True)

    prices = db.relationship('stockPrice', back_populates='ticker', cascade="all, delete", passive_deletes=True)

    def __init__(self, name, ticker):
        self.name = name
        self.ticker = ticker

    def __repr__(self):
        return '<record {} {}>'.format(self.name, self.ticker)

class stockPrice(db.Model):
    __tablename__ = 'stockPrice'
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False)

    ticker_fk = db.Column(db.String,db.ForeignKey('stockTicker.ticker', ondelete="CASCADE"), nullable=False)
    ticker = db.relationship('stockTicker', back_populates='prices')

    openPrice = db.Column(db.Float, nullable=False)
    highPrice = db.Column(db.Float, nullable=False)
    lowPrice = db.Column(db.Float, nullable=False)
    closePrice = db.Column(db.Float, nullable=False)
    volume = db.Column(db.Float, nullable=False)

    def __init__(self, date, ticker_fk, openPrice, highPrice, lowPrice, closePrice, volume):
        self.date = date
        self.ticker_fk = ticker_fk
        self.openPrice = openPrice
        self.highPrice = highPrice
        self.lowPrice = lowPrice
        self.closePrice = closePrice
        self.volume = volume
        

    def __repr__(self):
        return '<Price {} {}>'.format(self.date, self.ticker_fk)
