import datetime
from urllib.error import HTTPError
from sqlalchemy.exc import IntegrityError,InvalidRequestError,DataError
import psycopg2
from flask import (Blueprint, flash, g, make_response, redirect,
                   render_template, request, session, url_for)
from flaskapp import app, db, scheduler
from flaskapp.models import shortReport, stockPrice, stockTicker, stockBorrow
from flaskapp.shortSell.form import formTickerChoose

shortSell_bp = Blueprint('shortSell', __name__,
                         template_folder='templates/shortSell',
                         static_folder='static')


def saveShortSell(date=datetime.date.today()):  # date has to be in datetime format
    import urllib
    import pandas as pd
    year, month, day = str(date.year), str(date.month), str(date.day)
    if len(month) == 1: month = month.zfill(2)
    if len(day) == 1: day = day.zfill(2)

    url = "https://api2.sgx.com/sites/default/files/reports/short-sell/{0}/{1}/website_DailyShortSell{0}{1}{2}1815.txt".format(
        year, month, day)
    try:
        with urllib.request.urlopen(url) as reader:
            reader.readline()
            c = pd.read_fwf(reader, skipfooter=4, engine='python')
            c.columns = ['Security', 'ShortSaleVolume', 'Curr', 'ShortSaleValue']
            c.drop(columns=['Curr'], inplace=True)
        c['ShortSaleVolume'] = pd.to_numeric(c['ShortSaleVolume'], errors='coerce')
        c['ShortSaleValue'] = pd.to_numeric(c['ShortSaleValue'], errors='coerce')
        c = c.dropna()
        d = dict()
        for i in range(len(c)):
            d[c.iloc[i]['Security']] = [float(c.iloc[i]['ShortSaleVolume']),
                                        float(c.iloc[i]['ShortSaleValue'])]
        record = shortReport(date, d)
        db.session.add(record)
        db.session.commit()
    except (IntegrityError , HTTPError, InvalidRequestError) as e:
        app.logger.error(str(e))
    
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as reader:
            reader.readline()
            c = pd.read_fwf(reader, skipfooter=4, engine='python')
            c.columns = ['Security', 'ShortSaleVolume', 'Curr', 'ShortSaleValue']
            c.drop(columns=['Curr'], inplace=True)
        c['ShortSaleVolume'] = pd.to_numeric(c['ShortSaleVolume'], errors='coerce')
        c['ShortSaleValue'] = pd.to_numeric(c['ShortSaleValue'], errors='coerce')
        c = c.dropna()
        d = dict()
        for i in range(len(c)):
            d[c.iloc[i]['Security']] = [float(c.iloc[i]['ShortSaleVolume']),
                                        float(c.iloc[i]['ShortSaleValue'])]
        record = shortReport(date, d)
        db.session.add(record)
        db.session.commit()
    except (HTTPError, InvalidRequestError) as e:
        flash('Shortsell report not yet out')
        app.logger.error(str(e))
    except (IntegrityError) as e:
        flash('Shortsell already updated')
        app.logger.error(str(e))
    return


def saveSBL(date=datetime.date.today()):  # date has to be in datetime format
    year, month, day = str(date.year), str(date.month), str(date.day)
    if len(month) == 1: month = month.zfill(2)
    if len(day) == 1: day = day.zfill(2)

    import requests
    from bs4 import BeautifulSoup
    import pandas as pd

    page = requests.get("https://www1.cdp.sgx.com/sgx-cdp-web/lendingpool/show")
    soup = BeautifulSoup(page.content, 'html.parser')
    filein = soup.find(id="lendingpooltable")
    c = pd.read_html(filein.prettify())[0]

    try:
        c.drop(columns=['No.','Security Name','Lending Rate (%)', 'Borrowing Rate (%)'], inplace=True)
        c['Lending Pool'] = pd.to_numeric(c['Lending Pool'], errors='coerce')
        c = c.dropna()
        d = dict()
        for i in range(len(c)):
            d[c.iloc[i]['Security Code']] = float(c.iloc[i]['Lending Pool'])
        record = stockBorrow(date, d)
        db.session.add(record)
        db.session.commit()
        flash('SBL updated')
    except (InvalidRequestError) as e:
        flash('SBL failed to update')
        app.logger.error(str(e))
    except (IntegrityError) as e:
        flash('SBL already updated')
        app.logger.error(str(e))
    except:
        return


def savePrice(ticker_fk):
    import pandas as pd
    # try using pandas to read table first
    try:
        url = db.session.query(stockTicker.website)\
                .filter_by(ticker=ticker_fk).scalar()
        c = pd.read_html(url)[0][:-1]
    # else use beautiful soup to get data
    except:
        from requests import get
        from bs4 import BeautifulSoup
        page = get(url, headers={'User-Agent': 'Custom'})
        soup = BeautifulSoup(page.content, 'html.parser')
        c = []
        for tr in soup.find("table").children:
            for td in tr:
                c.append([])
                for i in td:
                    c[-1].append(i.text.replace(',',''))
        c = pd.DataFrame(c)
        c.columns = c.iloc[0]
        c=c[1:-1]
    
    # clean data
    c['Date'] = pd.to_datetime(c['Date'])
    c = c.dropna()
    c.reset_index(inplace = True)

    # get dates that are not yet in data base
    # else if date exist, use the latest date from db
    last_date = db.session.query(stockPrice.date)\
                  .filter(stockPrice.ticker_fk == ticker_fk)\
                  .order_by(stockPrice.date.desc()).first()
    if not last_date:
        last_date = datetime.date.today() - datetime.timedelta(days=100)
    else:
        last_date = last_date.date

    # If time is after 6pm then get prices for the day
    # else pop it from the list
    if datetime.datetime.now().hour < 18:
        c = c.iloc[1: , :]

    for currentDate in c['Date']:
        if currentDate <= last_date:
            break
        try:
            # float(c.iloc[i]['Open'])
            holder = c.loc[c['Date'] == currentDate]
            record = stockPrice(holder['Date'].iloc[0],
                            ticker_fk,
                            holder['Open'].iloc[0],
                            holder['High'].iloc[0],
                            holder['Low'].iloc[0],
                            holder['Close*'].iloc[0],
                            holder['Volume'].iloc[0])
            db.session.add(record)
            db.session.commit()
        except (IntegrityError, DataError, HTTPError, InvalidRequestError, ValueError) as e:
            app.logger.error(str(e))
            continue


def savePrices(tickerList):
    for ticker in tickerList:
        savePrice(ticker)


def get_tickerList():
    lt = db.session.query(stockTicker.ticker).filter(
        stockTicker.website != None).all()
    return [item for t in lt for item in t]


# populate DB with the missing short dates
@shortSell_bp.route('/shortSellValidatePrice', methods=('GET', 'POST'))
def shortSellValidatePrice(numDays=10):
    flash('Please wait')
    tickerList = get_tickerList()

    last_date = db.session.query(stockPrice.date)\
                .order_by(stockPrice.date.desc()).first().date

    records = db.session.query(stockPrice)\
                .filter(stockPrice.date >= (last_date - datetime.timedelta(days=numDays))).delete()
    db.session.commit()

    savePrices(tickerList)
    flash('Done validating')
    return redirect(url_for('initialiser.initialiserHome'))

# populate DB with the missing short dates
@shortSell_bp.route('/shortSellUpdateShort', methods=('GET', 'POST'))
def shortSellUpdateShort():
    date = datetime.date.today()
    last_date = db.session.query(shortReport.date).order_by(
        shortReport.date.desc()).first()[0]
    
    while last_date + datetime.timedelta(days=1) <= date:
        last_date = last_date + datetime.timedelta(days=1)
        saveShortSell(last_date)
    flash('Done')
    return redirect(url_for('initialiser.initialiserHome'))


@shortSell_bp.route('/shortSellUpdateAllPrice/', methods=('GET', 'POST'))
def shortSellUpdateAllPrice():
    stockList = get_tickerList()
    for myStock in stockList:
        savePrice(myStock)
    flash('Done for all')
    return redirect(url_for('initialiser.initialiserHome'))


@shortSell_bp.route('/shortSellSaveSBL/', methods=('GET', 'POST'))
def shortSellSaveSBL():
    saveSBL(datetime.date.today())
    flash('Done for all')
    return redirect(url_for('initialiser.initialiserHome'))


@shortSell_bp.route('/shortSellAll/', methods=('GET', 'POST'))
def shortSellAll():
    saveSBL(datetime.date.today())
    db.session.close()

    # part 2
    stockList = get_tickerList()
    for myStock in stockList:
        savePrice(myStock)
    db.session.close()

    # part 3
    saveShortSell(datetime.date.today())

    flash('Done for all')
    return redirect(url_for('initialiser.initialiserHome'))


#scheduler.add_job(func=saveShortSell, trigger="date", run_date=datetime.date.today() + datetime.timedelta(days=1), args=[datetime.date.today()])
#scheduler.add_job(func=savePrices, trigger="date", run_date=datetime.date.today() + datetime.timedelta(days=1), args=[get_tickerList()])
