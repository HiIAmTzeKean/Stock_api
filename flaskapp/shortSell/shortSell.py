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
    except (IntegrityError , HTTPError, InvalidRequestError) as e:
        flash('Shortsell failed to update')
        app.logger.error(str(e))
    return


def saveSBL(date=datetime.date.today()):  # date has to be in datetime format
    year, month, day = str(date.year), str(date.month), str(date.day)
    if len(month) == 1: month = month.zfill(2)
    if len(day) == 1: day = day.zfill(2)

    import requests
    page = requests.get("https://www1.cdp.sgx.com/sgx-cdp-web/lendingpool/show")
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(page.content, 'html.parser')
    filein = soup.find(id="lendingpooltable")
    import pandas as pd
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
    except (IntegrityError, InvalidRequestError) as e:
        flash('SBL failed to update')
        app.logger.error(str(e))
    except:
        return


def savePrice(ticker_fk):
    import pandas as pd
    url = db.session.query(stockTicker.website)\
            .filter_by(ticker=ticker_fk).scalar()
    c = pd.read_html(url)[0][:-1]
    c['Date'] = pd.to_datetime(c['Date'])

    # get dates that are not yet in data base
    last_date = db.session.query(stockPrice.date)\
                  .filter(stockPrice.ticker_fk == ticker_fk)\
                  .order_by(stockPrice.date.desc()).first()
    if not last_date:
        last_date = datetime.date.today() - datetime.timedelta(days=100)
    else:
        last_date = last_date[0]
    c['Volume'] = pd.to_numeric(c['Volume'], errors='coerce')
    for i in range(len(c)):
        if c['Date'][i] <= last_date:
            break
        try:
            float(c.iloc[i]['Open'])
            record = stockPrice(c.iloc[i]['Date'],
                            ticker_fk,
                            c.iloc[i]['Open'],
                            c.iloc[i]['High'],
                            c.iloc[i]['Low'],
                            c.iloc[i]['Close*'],
                            c.iloc[i]['Volume'])
            db.session.add(record)
            db.session.commit()
        except (IntegrityError, DataError, HTTPError, InvalidRequestError, ValueError) as e:
            app.logger.error(str(e))
            continue
    return


def savePrices(tickerList):
    for ticker in tickerList:
        savePrice(ticker)


def get_tickerList():
    lt = db.session.query(stockTicker.ticker).filter(
        stockTicker.website != None).all()
    return [item for t in lt for item in t]


# populate DB with the missing short dates
@shortSell_bp.route('/shortSellScheduler', methods=('GET', 'POST'))
def shortSellScheduler():
    date = datetime.date.today()
    last_date = db.session.query(shortReport.date).order_by(
        shortReport.date.desc()).first()[0]
    
    while last_date + datetime.timedelta(days=1) <= date:
        last_date = last_date + datetime.timedelta(days=1)
        saveShortSell(last_date)
    flash('Done')
    return redirect(url_for('initialiser.initialiserHome'))


# getting price for a specific ticker now
@shortSell_bp.route('/shortSellGetPrice/<ticker_fk>', methods=('GET', 'POST'))
def shortSellGetPrice(ticker_fk):
    savePrice(ticker_fk)
    return render_template('shortSellGetPrice.html', tickerName=str(ticker_fk))


@shortSell_bp.route('/shortSellUpdateAllPrice/', methods=('GET', 'POST'))
def shortSellUpdateAllPrice():
    stockList = get_tickerList()
    for myStock in stockList:
        savePrice(myStock)
    flash('Done for all')
    return redirect(url_for('initialiser.initialiserHome'))


@shortSell_bp.route('/shortSellGetWeekly', methods=('GET', 'POST'))
def shortSellGetWeekly():
    import pandas as pd
    import numpy as np
    stock = db.session.query(stockTicker.name).filter_by(ticker='BS6.SI').scalar()
    records = db.session.query(shortReport.stocks[stock],shortReport.date).filter(shortReport.stocks[stock].isnot(None)).all()
    records = np.transpose(records)
    vol,val = zip(*records[0])
    record = zip(records[1],vol,val)
    df = pd.DataFrame(record, columns=['Date', 'ShortSaleVolume', 'ShortSaleValues'])
    text =''
    sumVol = 0
    sumVal = 0
    for i in range(len(df)):
        sumVol += df.iloc[i]['ShortSaleVolume']
        sumVal += df.iloc[i]['ShortSaleValues']
        if df.iloc[i]['Date'].weekday() == 4:
            text+= 'for period of {} to {}\n'.format(df.iloc[i]['Date']- datetime.timedelta(days=4),df.iloc[i]['Date'])
            text+= 'val = {}\n'.format(sumVal)
            text+= 'vol = {}\n'.format(sumVol)
            sumVol = 0
            sumVal = 0  
    print(text)
    return text


@shortSell_bp.route('/shortSellGenerator/<ticker>', methods=('GET', 'POST'))
def shortSellGenerator(ticker):
    import pandas as pd
    import numpy as np
    import io
    import base64
    from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
    from matplotlib.figure import Figure
    import mplfinance as mpf
    from matplotlib.ticker import MultipleLocator,FuncFormatter
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates

    # choosing the stock I want to see
    stock = db.session.query(stockTicker.name).filter_by(ticker=ticker).scalar()
    if not stock:
        return 'Failed'
    
    # get all short record
    records = db.session.query(shortReport.stocks[stock],shortReport.date).filter(shortReport.stocks[stock].isnot(None)).all()
    records = np.transpose(records)
    vol,val = zip(*records[0])
    record = zip(records[1],vol,val)
    df = pd.DataFrame(record, columns=['Date', 'ShortSaleVolume', 'ShortSaleValues'])

    # get all price record
    records = db.session.query(stockPrice.date,
                               stockPrice.openPrice,
                               stockPrice.highPrice,
                               stockPrice.lowPrice,
                               stockPrice.closePrice,
                               stockPrice.volume).filter_by(ticker_fk=ticker).all()
    df2 = pd.DataFrame(records, columns=['Date', 'Open', 'High', 'Low', 'Close', 'Volume'])

    # normal plot
    df2['Date'] = pd.to_datetime(df2['Date'], format='%Y-%m-%d')
    df2.sort_values(by=['Date'], ascending=True, inplace=True)
    df2 = df2[df2['Date'] > pd.to_datetime('2020-12-07', format='%Y-%m-%d')]
    fig = mpf.figure(figsize=(16, 16))
    ax = fig.add_subplot(3, 2, 1)
    ax2 = fig.add_subplot(3, 2, 2, sharex=ax)
    mpf.plot(df2.set_index('Date'), type='candle', ax=ax, show_nontrading=True)

    # volume traded
    ax2.bar(df2['Date'], df2['Volume'])
    ax2.set_ylabel("Volume 10^6")
    plt.xticks(rotation=90)

    # ratio
    ax3 = fig.add_subplot(3, 2, 4, sharex=ax)
    df['Date'] = pd.to_datetime(df['Date'], format='%Y-%m-%d')
    df2 = df2.merge(df, how='left', on='Date')
    plt.xticks(rotation=90)
    ax3.bar(df2['Date'], df2['ShortSaleVolume']/df2['Volume'])
    ax3.set_ylabel("ShorVolume/Volume")
    ax3.yaxis.set_major_locator(MultipleLocator(0.05))

    # short ave price
    ax5 = fig.add_subplot(3, 2, 3, sharex=ax)
    plt.xticks(rotation=90)
    ax5.bar(df2['Date'], df2['ShortSaleValues']/df2['ShortSaleVolume'])
    ax5.set_ylabel("Short aggregate price")
    ax5.yaxis.set_major_locator(MultipleLocator(0.025))
    ax5.set_ylim((df2['ShortSaleValues']/df2['ShortSaleVolume']).min(),(df2['ShortSaleValues']/df2['ShortSaleVolume']).max()*1.01)

    # short vol
    ax4 = fig.add_subplot(3, 2, 6, sharex=ax)
    plt.xticks(rotation=90)
    ax4.bar(df2['Date'], df2['ShortSaleVolume'])
    ax4.set_ylabel("ShortVolume 10^6")
    ax4.xaxis.set_major_locator(MultipleLocator(7))
    ax4.xaxis.set_major_formatter(mdates.DateFormatter('%d-%m-%y'))

    # Format Y axis to millions
    ticks_y = FuncFormatter(lambda x, pos: '{0:g}'.format(x/1e6))
    ax4.yaxis.set_major_formatter(ticks_y)
    ax2.yaxis.set_major_formatter(ticks_y)

    # Set spaacing bewteen plots
    plt.subplots_adjust(hspace=0.2)

    # Convert plot to PNG image
    pngImage = io.BytesIO()
    FigureCanvas(fig).print_png(pngImage)

    # Encode PNG image to base64 string
    pngImageB64String = "data:image/png;base64,"
    pngImageB64String += base64.b64encode(pngImage.getvalue()).decode('utf8')

    return render_template('shortSellGenerator.html', name='new_plot', myimage=pngImageB64String)


@shortSell_bp.route('/shortSellGenerator2/<ticker>', methods=('GET', 'POST'))
def shortSellGenerator2(ticker):
    import pandas as pd
    import numpy as np

    # choosing the stock I want to see
    stock = db.session.query(stockTicker.name).filter_by(ticker=ticker).scalar()
    if not stock:
        return 'Failed'
    
    # get all short record
    records = db.session.query(shortReport.stocks[stock],shortReport.date).filter(shortReport.stocks[stock].isnot(None)).all()
    records = np.transpose(records)
    vol,val = zip(*records[0])
    record = zip(records[1],vol,val)
    df = pd.DataFrame(record, columns=['Date', 'ShortSaleVolume', 'ShortSaleValues'])
    
    # get all price record
    records = db.session.query(stockPrice.date,
                               stockPrice.openPrice,
                               stockPrice.highPrice,
                               stockPrice.lowPrice,
                               stockPrice.closePrice,
                               stockPrice.volume).filter_by(ticker_fk=ticker).all()
    df2 = pd.DataFrame(records, columns=['Date', 'Open', 'High', 'Low', 'Close', 'Volume'])

    # merge df and df2
    df2 = df2.merge(df, how='left', on='Date')

    # convert date to datetime 
    # followed by converting to epoch in micro seconds
    df2['Date'] = df2['Date'].apply(lambda x: datetime.datetime.combine(x, datetime.time()).timestamp()*1000)
    df2.sort_values(by=['Date'], ascending=True, inplace=True)

    # get short price
    df2['shortPrice'] = df2['ShortSaleValues'].divide(df2['ShortSaleVolume'],fill_value=0)
    df2['shortRatio'] = df2['ShortSaleVolume'].divide(df2['Volume'],fill_value=0)
    df2['shortPrice'].fillna(method='bfill', inplace=True)
    df2['ShortSaleVolume'].fillna(0, inplace=True)

    return render_template('shortSellChartJS.html',
                        dataOHLC = df2[['Date', 'Open', 'High', 'Low', 'Close']].values.tolist(),
                        dataShortPrice = df2[['Date', 'shortPrice']].values.tolist(),
                        dataVol = df2[['Date','Volume']].values.tolist(),
                        dataShortVol = df2[['Date','ShortSaleVolume']].values.tolist(),
                        dataShortRatio = df2[['Date','shortRatio']].values.tolist(),
                        dataMinDate = df2['Date'].min(),
                        dataMaxDate = df2['Date'].max(),
                        dates=df2[['Date']].values.tolist())

@shortSell_bp.route('/shortSellViewer/', methods=('GET', 'POST'))
def shortSellViewer():
    form = formTickerChoose()
    tickerList = db.session.query(stockTicker.name, stockTicker.ticker).filter(stockTicker.website!=None).all()
    form.ticker.choices = [(tickerRecord.ticker,tickerRecord.name) for tickerRecord in tickerList]
    if form.validate_on_submit():
        return redirect(url_for('shortSell.shortSellGenerator2', ticker=form.ticker.data))
    return render_template('shortSellViewer.html', form=form)
    

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
