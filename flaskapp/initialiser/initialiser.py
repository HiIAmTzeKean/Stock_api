import datetime
from flask import (Blueprint, flash, g, make_response, redirect,
                   render_template, request, session, url_for)
from flaskapp import db, scheduler
from flaskapp.models import shortReport, stockPrice, stockTicker
from flaskapp.initialiser.form import formTickerEdit

initialiser_bp = Blueprint('initialiser', __name__,
                           template_folder='templates', static_folder='static')


@initialiser_bp.route('/initialiserHome', methods=('GET', 'POST'))
def initialiserHome():
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

