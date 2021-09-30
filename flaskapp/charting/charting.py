import datetime
from urllib.error import HTTPError
from sqlalchemy.exc import IntegrityError,InvalidRequestError,DataError
import psycopg2
from flask import (Blueprint, flash, g, make_response, redirect,
                   render_template, request, session, url_for)
from flaskapp import app, db, scheduler
from flaskapp.models import shortReport, stockPrice, stockTicker, stockBorrow
from flaskapp.charting.form import formTickerChoose

charting_bp = Blueprint('charting', __name__,
                         template_folder='templates/charting',
                         static_folder='static')

@charting_bp.route('/chartingGenerator/<ticker>', methods=('GET', 'POST'))
def chartingGenerator(ticker):
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

    return render_template('chartingGenerator.html', name='new_plot', myimage=pngImageB64String)


@charting_bp.route('/chartingGenerator2/<ticker>', methods=('GET', 'POST'))
def chartingGenerator2(ticker):
    import pandas as pd
    from numpy import transpose

    # choosing the stock I want to see
    stock = db.session.query(stockTicker.name).filter_by(ticker=ticker).scalar()
    if not stock:
        return 'Failed'
    
    # get all short record
    records = db.session.query(shortReport.stocks[stock],shortReport.date).filter(shortReport.stocks[stock].isnot(None)).all()
    records = transpose(records)
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
    df2['shortRatio'] = df2['ShortSaleVolume'].divide(df2['Volume'])
    df2[['Volume', 'ShortSaleVolume']] = df2[['Volume', 'ShortSaleVolume']].divide(1000000)
    df2['shortPrice'].fillna(method='bfill', inplace=True)
    df2.fillna({'ShortSaleVolume':0,'Volume':0,'shortRatio':0}, inplace=True)
    df2['shortPrice'] = df2['shortPrice'].astype(float).round(3)

    return render_template('chartingChartJS.html',
                        dataOHLC = df2[['Date', 'Open', 'High', 'Low', 'Close']].values.tolist(),
                        dataShortPrice = df2[['Date', 'shortPrice']].values.tolist(),
                        dataVol = df2[['Date','Volume']].values.tolist(),
                        dataShortVol = df2[['Date','ShortSaleVolume']].values.tolist(),
                        dataShortRatio = df2[['Date','shortRatio']].values.tolist(),
                        dataMinDate = df2['Date'].min(),
                        dataMaxDate = df2['Date'].max(),
                        dates=df2[['Date']].values.tolist())

@charting_bp.route('/chartingViewer/', methods=('GET', 'POST'))
def chartingViewer():
    form = formTickerChoose()
    tickerList = db.session.query(stockTicker.name, stockTicker.ticker).filter(stockTicker.website!=None).all()
    form.ticker.choices = [(tickerRecord.ticker,tickerRecord.name) for tickerRecord in tickerList]
    if form.validate_on_submit():
        if request.form.get('selection') == 'new':
            return redirect(url_for('charting.chartingGenerator2', ticker=form.ticker.data))
        return redirect(url_for('charting.chartingGenerator', ticker=form.ticker.data))
    return render_template('chartingViewer.html', form=form)
    
