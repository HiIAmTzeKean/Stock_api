from flaskapp import db
from datetime import datetime
from sqlalchemy.dialects.postgresql import JSON
import json


class shortReport(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False)
    stocks = db.Column(JSON, nullable=False)

    def __init__(self, date, stocks):
        self.date = date
        self.stocks = stocks

    def __repr__(self):
        return '<Short record {}>'.format(self.date)

class stockTicker(db.Model):
    __table_args__ = (
        # this can be db.PrimaryKeyConstraint if you want it to be a primary key
        db.UniqueConstraint('name', 'ticker'),
      )
    name = db.Column(db.String, nullable=False)
    ticker = db.Column(db.String, primary_key=True)
    website = db.Column(db.String)

    prices = db.relationship('stockPrice', back_populates='tickers', cascade="all, delete", passive_deletes=True)

    def __init__(self, name, ticker):
        self.name = name
        self.ticker = ticker

    def __repr__(self):
        return '<Record {} {}>'.format(self.name, self.ticker)

class stockPrice(db.Model):
    
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False)
    openPrice = db.Column(db.Float, nullable=False)
    highPrice = db.Column(db.Float, nullable=False)
    lowPrice = db.Column(db.Float, nullable=False)
    closePrice = db.Column(db.Float, nullable=False)
    volume = db.Column(db.Float, nullable=False)

    tickers = db.relationship('stockTicker', back_populates='prices')
    ticker_fk = db.Column(db.String, db.ForeignKey('stock_ticker.ticker', ondelete="CASCADE"))

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


class Users(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String)
    def __init__(self):
        pass
    