import datetime
from flask import (Blueprint, flash, g, make_response, redirect,
                   render_template, request, session, url_for)
from flaskapp import db, scheduler
from flaskapp.models import shortReport, stockPrice, stockTicker

shortSell_bp = Blueprint('shortSell', __name__,
                          template_folder='templates', static_folder='static')

def saveShortSell(date=datetime.date.today()): # date has to be in datetime format
  import urllib
  import pandas as pd
  import json
  year,month,day = str(date.year),str(date.month),str(date.day-1)
  if len(month)==1: month=month.zfill(2)
  if len(day)==1: day=day.zfill(2)
  
  url = "https://api2.sgx.com/sites/default/files/reports/short-sell/{0}/{1}/website_DailyShortSell{0}{1}{2}1815.txt".format(year,month,day)
  try:
    # format data into JSON
    with urllib.request.urlopen(url) as reader:
      reader.readline()
      c = pd.read_fwf(reader,skipfooter=4,engine='python')
      c.drop(columns=['Curr'],inplace=True)

    d = dict()
    for i in range(len(c)):
        d[c.iloc[i]['Security']]=[float(c.iloc[i]['ShortSaleVolume']),float(c.iloc[i]['ShortSaleValue'])]
    record = shortReport(date,json.dumps(d))
    db.session.add(record)
    db.session.commit()
  except: print(date)

scheduler.add_job(func=saveShortSell, trigger="date", run_date=datetime.date.today(), args=[datetime.date.today()])

#temp for set up
@shortSell_bp.route('/shortSellScheduler', methods=('GET', 'POST'))
def shortSellScheduler():
  date = datetime.date.today()
  last_date = db.session.query(shortReport.date).order_by(shortReport.date.desc()).first()[0]
  while last_date + datetime.timedelta(days=1) < date:
    last_date = last_date + datetime.timedelta(days=1)
    saveShortSell(date)
  # date_last = datetime.datetime.strptime('2020-12-17', "%Y-%m-%d").date()
  # date_end = datetime.date.today()
  # datelist = db.session.query(shortReport.date).order_by(shortReport.date.asc()).all()
  # datelist2 = []
  # for i in datelist:
  #   datelist2.append(i.date)
  # while date_last<date_end:
  #   if date_last in datelist2:
  #     pass
  #   else:
  #     saveShortSell(date_last)
  #   date_last = date_last + datetime.timedelta(days=1)
  return 'h'

# creating once to generate the ticker
@shortSell_bp.route('/shortSellTickerCreator', methods=('GET', 'POST'))
def shortSellTickerCreator():
  import pandas as pd
  import pathlib
  
  filename = '\SGXsymbol.txt'
  c=pd.read_csv(str(pathlib.Path().absolute()) + filename, delimiter = "\t")

  for i in range(len(c)):
    record = stockTicker(name=c.iloc[i]['Description'], ticker=c.iloc[i]['Symbol'])
    db.session.add(record)
    db.session.commit()
  return (str(pathlib.Path().absolute()) + filename)


# getting price for a specific ticker now
@shortSell_bp.route('/shortSellGetPrice', methods=('GET', 'POST'))
def shortSellGetPrice():
  import pandas as pd
  ticker_fk = 'BS6.SI'

  url = 'https://sg.finance.yahoo.com/quote/BS6.SI/history?p=BS6.SI&.tsrc=fin-srch'
  c=pd.read_html(url)[0][:-1]
  c['Date'] = pd.to_datetime(c['Date'])

  # get dates that are not yet in data base
  last_date = db.session.query(stockPrice.date).filter(stockPrice.ticker_fk==ticker_fk).order_by(stockPrice.date.desc()).first()[0]

  for i in range(len(c)):
    try:
      float(c.iloc[i]['Open'])
      if c['Date'][i]<=last_date:
        print(c['Date'][i])
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
    #db.session.add(record)
    #db.session.commit()
  return 'Done'

# view graph
@shortSell_bp.route('/shortSellViewer', methods=('GET', 'POST'))
def shortSellViewer():
  import pandas as pd
  import io
  import base64
  from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
  from matplotlib.figure import Figure
  import matplotlib.dates as mpl_dates
  import mplfinance as mpf
  import matplotlib.pyplot as plt
  from matplotlib.ticker import MultipleLocator
  import json

  # choosing the stock I want to see
  ticker = 'BS6.SI'
  stock = 'YZJ Shipbldg SGD'

  # get all stock short record
  df = pd.DataFrame(columns=['Date','ShortSaleVolume','ShortSaleValues'])
  columns = list(df)
  data=[]
  
  records = db.session.query(shortReport).all()
  for record in records:
    stockList = json.loads(record.stocks)
    values = [record.date,stockList[stock][0],stockList[stock][1]]
    data.append(dict(zip(columns, values)))
  df = df.append(data, True)

  # get all price record
  df2 = pd.DataFrame(columns=['Date', 'Open', 'High', 'Low', 'Close','Volume'])
  columns = list(df2)
  data=[]

  records = db.session.query(stockPrice).filter_by(ticker_fk=ticker).all()
  for record in records:
      values = [record.date,record.openPrice,record.highPrice,record.lowPrice,record.closePrice,record.volume]
      data.append(dict(zip(columns, values)))
  df2 = df2.append(data, True)


  #test
  df2['Date'] = pd.to_datetime(df2['Date'],format = '%Y-%m-%d')
  df2.sort_values(by=['Date'], ascending=True, inplace=True)
  fig = mpf.figure(figsize=(15,10))
  ax = fig.add_subplot(3,1,1)
  ax2 = fig.add_subplot(3, 1, 2, sharex = ax) 
  mpf.plot(df2.set_index('Date'), type='candle',mav=(3,6,9), ax=ax, volume=ax2)

  ax3 = fig.add_subplot(3, 1, 3)
  df['Date'] = pd.to_datetime(df['Date'],format = '%Y-%m-%d')
  df2 = df2.merge(df, how='left', on='Date')
  df2.sort_values(by=['Date'], ascending=True, inplace=True)
  df2.drop(['Volume', 'ShortSaleValues'], axis=1, inplace=True)
  df2.rename(columns={"ShortSaleVolume": "Volume"}, inplace=True)
  print(df2)
  mpf.plot(df2.set_index('Date'), type='candle',ax=ax3, volume=ax3)
  # result=10/0
  # ax3.plot(df['Date'], df['ShortSaleValues'], "r-")

  # Generate plot
  # fig = Figure(figsize=(15,10))
  # axis = fig.add_subplot(2, 1, 1)
  # axis2 = fig.add_subplot(2, 1, 2, sharex = axis)
  # candlestick_ohlc(axis, df2.values, width=0.6, colorup='green', colordown='red', alpha=0.8)
  # axis.set_title("YZJ Shipbldg SGD")
  # axis.set_xlabel("Date")
  # axis.set_ylabel("Price")
  # axis.grid()

  # axis2.plot(df['Date'], df['ShortSaleValues'], "r-")
  # axis2.plot(df2['Date'], df2['Volume']/40, "b-")
  # axis2.grid()

  #date_format = mpl_dates.DateFormatter('%d-%m-%Y')
  #axis.xaxis.set_major_locator(MultipleLocator(5))
  #axis.xaxis.set_major_formatter(date_format)
  #fig.autofmt_xdate()

  # Convert plot to PNG image
  pngImage = io.BytesIO()
  FigureCanvas(fig).print_png(pngImage)
  
  # Encode PNG image to base64 string
  pngImageB64String = "data:image/png;base64,"
  pngImageB64String += base64.b64encode(pngImage.getvalue()).decode('utf8')

  return render_template('shortSellViewer.html', name = 'new_plot', myimage=pngImageB64String)