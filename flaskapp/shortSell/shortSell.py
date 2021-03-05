import datetime
from flask import (Blueprint, flash, g, make_response, redirect,
                   render_template, request, session, url_for)
from flaskapp import db, scheduler
from flaskapp.models import shortReport

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
  except:
    print('nope')
  print(date)

scheduler.add_job(func=saveShortSell, trigger="date", run_date=datetime.date.today(), args=[datetime.date.today()])

@shortSell_bp.route('/shortSellScheduler', methods=('GET', 'POST'))
def shortSellScheduler():
  import urllib
  import pandas as pd
  import json
  date = datetime.date.today() - datetime.timedelta(days=30)  

  # add previous 1 month
  for i in range(30):
    date = date + datetime.timedelta(days=1)
    saveShortSell(date)
  return 'h'

@shortSell_bp.route('/shortSellViewer', methods=('GET', 'POST'))
def shortSellViewer():
  import io
  import base64
  from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
  from matplotlib.figure import Figure
  import json

  # choosing the stock I want to see
  stock = 'YZJ Shipbldg SGD'

  # get all stock record
  records = db.session.query(shortReport).all()
  print(records)
  
  ShortSaleVolume = []
  ShortSaleValues = []
  day = []
  for record in records:
    stockList = json.loads(record.stocks)
    day.append(record.date)
    ShortSaleVolume.append(stockList[stock][0])
    ShortSaleValues.append(stockList[stock][1])
  # Generate plot
  fig = Figure(figsize=(10,10))
  axis = fig.add_subplot(1, 1, 1)
  axis.set_title("YZJ Shipbldg SGD")
  axis.set_xlabel("Date")
  axis.set_ylabel("Short")
  axis.grid()
  axis.plot(day, ShortSaleVolume, "r-")
  axis.plot(day, ShortSaleValues, "b-")

  # Convert plot to PNG image
  pngImage = io.BytesIO()
  FigureCanvas(fig).print_png(pngImage)
  
  # Encode PNG image to base64 string
  pngImageB64String = "data:image/png;base64,"
  pngImageB64String += base64.b64encode(pngImage.getvalue()).decode('utf8')

  return render_template('shortSellViewer.html', name = 'new_plot', myimage=pngImageB64String)