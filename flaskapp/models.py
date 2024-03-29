from flaskapp import db, app, migrate
from datetime import datetime
from sqlalchemy.dialects.postgresql import JSONB

class shortReport(db.Model):
    __table_args__ = (db.UniqueConstraint('date'),)
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False)

    # --- (name, [vol, value])
    stocks = db.Column(JSONB, nullable=False)

    def __init__(self, date, stocks):
        self.date = date
        self.stocks = stocks

    def __repr__(self):
        return '<Short record {}>'.format(self.date)


class stockTicker(db.Model):
    __table_args__ = (
        # this can be db.PrimaryKeyConstraint if you want it to be a primary key
        db.UniqueConstraint('name', 'ticker', 'isin'),
      )
    name = db.Column(db.String, nullable=False)
    ticker = db.Column(db.String, primary_key=True)
    isin = db.Column(db.String)
    website = db.Column(db.String)

    prices = db.relationship('stockPrice', back_populates='tickers', cascade="all, delete", passive_deletes=True)
    quaterlyResults = db.relationship('stockQuaterlyResults', back_populates='tickers', cascade="all, delete", passive_deletes=True)
    yearlyResults = db.relationship('stockYearlyResults', back_populates='tickers', cascade="all, delete", passive_deletes=True)

    def __init__(self, name, ticker):
        self.name = name
        self.ticker = ticker

    def __repr__(self):
        return '<Record {} {}>'.format(self.name, self.ticker)


class stockPrice(db.Model):
    __table_args__ = (
        db.UniqueConstraint('date', 'ticker_fk', name='unique_price'),
      )
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


class stockBorrow(db.Model):
    __table_args__ = (db.UniqueConstraint('date'),)
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False)

    # --- (name, [vol, borrrowrate])
    stocks = db.Column(JSONB, nullable=False)

    def __init__(self, date, stocks):
        self.date = date
        self.stocks = stocks

    def __repr__(self):
        return '<SBL record {}>'.format(self.date)


class stockQuaterlyResults(db.Model):
    __tablename__ = 'stockQuaterlyResults'
    tickers = db.relationship('stockTicker', back_populates='quaterlyResults')
    ticker_fk = db.Column(db.String, db.ForeignKey('stock_ticker.ticker', ondelete="CASCADE"), primary_key=True)

    date = db.Column(db.Date, nullable=False, primary_key=True)

    report = db.Column(JSONB, nullable=False)

    def __init__(self, ticker_fk, date, report):
        self.ticker_fk = ticker_fk
        self.date = date
        self.report = report

    def __repr__(self):
        return '<quaterlyResults record {}>'.format(self.date)

class stockYearlyResults(db.Model):
    __tablename__ = 'stockYearlyResults'
    tickers = db.relationship('stockTicker', back_populates='yearlyResults')
    ticker_fk = db.Column(db.String, db.ForeignKey('stock_ticker.ticker', ondelete="CASCADE"), primary_key=True)

    date = db.Column(db.Date, nullable=False, primary_key=True)

    report = db.Column(JSONB, nullable=False)

    def __init__(self, ticker_fk, date, report):
        self.ticker_fk = ticker_fk
        self.date = date
        self.report = report

    def __repr__(self):
        return '<quaterlyResults record {}>'.format(self.date)

class Users(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String)
    def __init__(self):
        pass
    