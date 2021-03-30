import datetime
from flask import (Blueprint, flash, g, make_response, redirect,
                   render_template, request, session, url_for)
from flaskapp import db, scheduler
from flaskapp.models import shortReport, stockPrice, stockTicker

initialiser_bp = Blueprint('initialiser', __name__,
                           template_folder='templates', static_folder='static')


@initialiser_bp.route('/initialiserHome', methods=('GET', 'POST'))
def initialiserHome():
    records = db.session.query(shortReport.stocks['YZJ Shipbldg SGD'],shortReport.date).first()
    print(records[0])
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
