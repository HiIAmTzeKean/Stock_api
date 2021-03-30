import datetime
from flask import (Blueprint, flash, g, make_response, redirect,
                   render_template, request, session, url_for)
from flaskapp import db, scheduler
from flaskapp.models import shortReport, stockPrice, stockTicker

shortSell_bp = Blueprint('shortSell', __name__,
                         template_folder='templates', static_folder='static')


def saveShortSell(date=datetime.date.today()):  # date has to be in datetime format
    import urllib
    import pandas as pd
    import json
    year, month, day = str(date.year), str(date.month), str(date.day-1)
    if len(month) == 1:
        month = month.zfill(2)
    if len(day) == 1:
        day = day.zfill(2)

    url = "https://api2.sgx.com/sites/default/files/reports/short-sell/{0}/{1}/website_DailyShortSell{0}{1}{2}1815.txt".format(
        year, month, day)
    try:
        # format data into JSON
        with urllib.request.urlopen(url) as reader:
            reader.readline()
            c = pd.read_fwf(reader, skipfooter=4, engine='python')
            c.drop(columns=['Curr'], inplace=True)

        d = dict()
        for i in range(len(c)):
            d[c.iloc[i]['Security']] = [
                float(c.iloc[i]['ShortSaleVolume']), float(c.iloc[i]['ShortSaleValue'])]
        record = shortReport(date, json.dumps(d))
        db.session.add(record)
        db.session.commit()
    except:
        print(date)


def savePrice(ticker_fk):
    import pandas as pd
    url = db.session.query(stockTicker.website).filter_by(
        ticker=ticker_fk).scalar()
    c = pd.read_html(url)[0][:-1]
    c['Date'] = pd.to_datetime(c['Date'])

    # get dates that are not yet in data base
    last_date = db.session.query(stockPrice.date).filter(
        stockPrice.ticker_fk == ticker_fk).order_by(stockPrice.date.desc()).first()[0]

    for i in range(len(c)):
        try:
            float(c.iloc[i]['Open'])
            if c['Date'][i] <= last_date:
                break
        except ValueError:
            continue
        record = stockPrice(c.iloc[i]['Date'],
                            ticker_fk,
                            c.iloc[i]['Open'],
                            c.iloc[i]['High'],
                            c.iloc[i]['Low'],
                            c.iloc[i]['Close*'],
                            c.iloc[i]['Volume'])
        db.session.add(record)
    db.session.commit()
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
    while last_date + datetime.timedelta(days=1) < date:
        last_date = last_date + datetime.timedelta(days=1)
        saveShortSell(last_date)
    return 'h'


# getting price for a specific ticker now
@shortSell_bp.route('/shortSellGetPrice/<ticker_fk>', methods=('GET', 'POST'))
def shortSellGetPrice(ticker_fk):
    savePrice(ticker_fk)
    return 'Done'

# view graph


@shortSell_bp.route('/shortSellViewer', methods=('GET', 'POST'))
def shortSellViewer():
    import pandas as pd
    import io
    import base64
    from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
    from matplotlib.figure import Figure
    import mplfinance as mpf
    from matplotlib.ticker import MultipleLocator
    import matplotlib.pyplot as plt
    import json

    # choosing the stock I want to see
    ticker = 'BS6.SI'
    stock = 'YZJ Shipbldg SGD'

    # get all stock short record
    df = pd.DataFrame(columns=['Date', 'ShortSaleVolume', 'ShortSaleValues'])
    columns = list(df)
    data = []

    records = db.session.query(shortReport).all()
    for record in records:
        stockList = json.loads(record.stocks)
        values = [record.date, stockList[stock][0], stockList[stock][1]]
        data.append(dict(zip(columns, values)))
    df = df.append(data, True)

    # get all price record
    df2 = pd.DataFrame(
        columns=['Date', 'Open', 'High', 'Low', 'Close', 'Volume'])
    columns = list(df2)
    data = []

    records = db.session.query(stockPrice).filter_by(ticker_fk=ticker).all()
    print(db.session.query(stockPrice).filter_by(ticker_fk='BS6.SI').all())
    for record in records:
        values = [record.date, record.openPrice, record.highPrice,
                  record.lowPrice, record.closePrice, record.volume]
        data.append(dict(zip(columns, values)))
    df2 = df2.append(data, True)

    # normal plot
    df2['Date'] = pd.to_datetime(df2['Date'], format='%Y-%m-%d')
    df2.sort_values(by=['Date'], ascending=True, inplace=True)
    df2 = df2[df2['Date'] > pd.to_datetime('2020-12-07', format='%Y-%m-%d')]
    fig = mpf.figure(figsize=(15, 15))
    ax = fig.add_subplot(3, 1, 1)
    ax2 = fig.add_subplot(3, 1, 2, sharex=ax)
    mpf.plot(df2.set_index('Date'), type='candle', mav=(
        3, 6, 9), ax=ax, volume=ax2, show_nontrading=True)
    ax.xaxis.set_major_locator(MultipleLocator(7))
    ax2.xaxis.set_major_locator(MultipleLocator(7))
    ax2.yaxis.set_major_locator(MultipleLocator(20*1000000))
    plt.xticks(rotation=90)

    # short volume
    ax3 = fig.add_subplot(3, 1, 3)
    df['Date'] = pd.to_datetime(df['Date'], format='%Y-%m-%d')
    df['Date'] = df['Date'] - pd.DateOffset(1)
    df2 = df2.merge(df, how='left', on='Date')
    df2.sort_values(by=['Date'], ascending=True, inplace=True)
    df2.drop(['Volume', 'ShortSaleValues'], axis=1, inplace=True)
    df2.rename(columns={"ShortSaleVolume": "Volume"}, inplace=True)
    # print(df2.iloc[-10:-1])
    mpf.plot(df2.set_index('Date'), type='candle',
             ax=ax3, volume=ax3, show_nontrading=True)
    ax3.xaxis.set_major_locator(MultipleLocator(7))
    ax3.yaxis.set_major_locator(MultipleLocator(2*1000000))
    plt.xticks(rotation=90)

    # Convert plot to PNG image
    pngImage = io.BytesIO()
    FigureCanvas(fig).print_png(pngImage)

    # Encode PNG image to base64 string
    pngImageB64String = "data:image/png;base64,"
    pngImageB64String += base64.b64encode(pngImage.getvalue()).decode('utf8')

    return render_template('shortSellViewer.html', name='new_plot', myimage=pngImageB64String)


scheduler.add_job(func=saveShortSell, trigger="date", run_date=datetime.date.today() + datetime.timedelta(days=1), args=[datetime.date.today()])
scheduler.add_job(func=savePrices, trigger="date", run_date=datetime.date.today() + datetime.timedelta(days=1), args=[get_tickerList()])
