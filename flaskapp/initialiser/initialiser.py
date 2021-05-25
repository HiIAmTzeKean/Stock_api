import datetime
from flask import (Blueprint, flash, g, make_response, redirect,
                   render_template, request, session, url_for)
from flaskapp import db, scheduler
from flaskapp.models import shortReport, stockPrice, stockTicker
from flaskapp.initialiser.form import formTickerEdit
from flaskapp.shortSell.shortSell import shortSellAll

initialiser_bp = Blueprint('initialiser', __name__,
                           template_folder='templates', static_folder='static')


@initialiser_bp.route('/initialiserHome', methods=('GET', 'POST'))
def initialiserHome():
    # constituents = ['Ascendas Reit', 'CapitaLand']
    # temp = []
    # records = db.session.query(shortReport.stocks,shortReport.date).limit(5).all()
    # for record in records:
    #     for item in constituents:
    #         temp.append([record.stocks[item][1],item,record.date])
    # records = db.session.query(shortReport.stocks['Ascendas Reit'],shortReport.stocks['CapitaLand'],shortReport.date).limit(1).all()
    currentTime = datetime.datetime.now().hour
    if currentTime > 18:
        shortSellAll()
    return render_template('initialiserHome.html')


# creating once to generate the ticker
@initialiser_bp.route('/initialiserSellTickerCreator', methods=('GET', 'POST'))
def initialiserSellTickerCreator():
    import pandas as pd
    from pathlib import Path

    filename = url_for('static', filename='SGXsymbol.txt')
    c = pd.read_csv(str(Path().absolute()) + filename, delimiter="\t")

    for i in range(len(c)):
        record = stockTicker(
            name=c.iloc[i]['Description'], ticker=c.iloc[i]['Symbol'])
        db.session.add(record)
        db.session.commit()
    return (str(Path().absolute()) + filename)


@initialiser_bp.route('/initialiserChangeName', methods=('GET', 'POST'))
def initialiserChangeName():
    form = formTickerEdit()
    if form.validate_on_submit():
        record = db.session.query(stockTicker).filter_by(ticker=form.ticker.data).first()
        if record:
            form.populate_obj(record)
            db.session.commit()
            flash('Added {} {}'.format(form.ticker.data,form.name.data))
            return redirect(url_for('shortSell.shortSellGetPrice', ticker_fk=form.ticker.data))
        return 'Not valid ticker'

    return render_template('initialiserChangeName.html', form=form)


def addISIN():
    import requests
    page = requests.get("https://www1.cdp.sgx.com/sgx-cdp-web/lendingpool/show")
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(page.content, 'html.parser')
    filein = soup.find(id="lendingpooltable")
    import pandas as pd
    c = pd.read_html(filein.prettify())[0]
    c.set_index('Security Name', inplace = True)

    tickerList = db.session.query(stockTicker).all()
    for item in tickerList:
        try:
            item.isin = c.loc[str(item.name).upper()]['Security Code']
            db.session.commit()
        except Exception as e:
            # print(c.loc[str(item.name).capitalize()]['Security Code'])
            print(e)
