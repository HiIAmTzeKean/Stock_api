import datetime
from flask import (Blueprint, flash, g, make_response, redirect,
                   render_template, request, session, url_for)
from flaskapp import db, scheduler
from flaskapp.models import stockTicker, stockQuaterlyResults, stockYearlyResults
from sqlalchemy.exc import IntegrityError,InvalidRequestError,DataError
from flaskapp.financials.helper import updateAllResultTable
import pandas as pd


financials_bp = Blueprint('financials', __name__,
                           template_folder='templates', static_folder='static')


@financials_bp.route('/financialsHome', methods=('GET', 'POST'))
def financialsHome():
    period='Quarterly'
    ticker = 'BS6.SI'
    updateAllResultTable(ticker,period=period)
    return ticker

@financials_bp.route('/financialsScanQuart', methods=('GET', 'POST'))
def financialsScanQuart():
    import pandas as pd
    import numpy as np
    import os
    ticker='E28.SI'
    report = os.path.join(os.getcwd(), "flaskapp/static/files", "compiledFrenken.csv")
    report = pd.read_csv(report,index_col=0)
    report.columns=report.loc['date']
    report.drop('date',axis=0,inplace=True)

    for count,i in enumerate(report):
        db.session.add(stockQuaterlyResults(ticker,i,report.iloc[:,count].astype('int64').to_dict()))
    db.session.commit()
    return 'great'

@financials_bp.route('/financialsScanYear', methods=('GET', 'POST'))
def financialsScanYear():
    import pandas as pd
    import numpy as np
    import os
    ticker='E28.SI'
    report = os.path.join(os.getcwd(), "flaskapp/static/files", "compiledFrenken.csv")
    report = pd.read_csv(report,index_col=0)
    report.columns=report.loc['date']
    report.drop('date',axis=0,inplace=True)

    for count,i in enumerate(report):
        db.session.add(stockYearlyResults(ticker,i,report.iloc[:,count].astype('int64').to_dict()))
    db.session.commit()
    return 'great'

@financials_bp.route('/financialsYearlyPerformance', methods=('GET', 'POST'))
def financialsPerformance():
    from collections import defaultdict
    ticker = 'E28.SI'
    period='Yearly'
    if period == 'Quarterly':
        reports = db.session.query(stockQuaterlyResults.report, stockQuaterlyResults.date)\
                .filter_by(ticker_fk=ticker).all()
    else:
        reports = db.session.query(stockYearlyResults.report, stockYearlyResults.date)\
                .filter_by(ticker_fk=ticker).all()
    
    reports,dates = list(zip(*reports))
    holder = defaultdict(list)
    for i in reports[-1]:
        for item in reports:
            holder[i].append(item.get(i))
    holder = pd.DataFrame(holder).transpose()

    evaluator = stockEvaluator(holder,dates)

    return render_template('financialsYearlyPerformance.html',
                            ticker=ticker,
                            roa = evaluator[['date', 'roa']].values.tolist(),
                            net_profit_margin = evaluator[['date', 'net profit margin']].values.tolist(),
                            gross_profit_margin = evaluator[['date', 'gross profit margin']].values.tolist(),
                            #------ debt ------
                            debt_asset = evaluator[['date', 'debt asset']].values.tolist(),
                            equity = evaluator[['date', 'roa']].values.tolist(),
                            gearing = evaluator[['date', 'gearing']].values.tolist(),
                            #-------- management ---------
                            asset_turnover = evaluator[['date', 'asset turnover']].values.tolist(),
                            #-------- investor -------
                            roc = evaluator[['date', 'roc']].values.tolist(),
                            roe = evaluator[['date', 'roe']].values.tolist(),
                            #
                            revenue = evaluator[['date', 'totalRevenue']].values.tolist(),
                            cost = evaluator[['date', 'costOfRevenue']].values.tolist(),
                            profit = evaluator[['date', 'grossProfit']].values.tolist(),
                            net_income = evaluator[['date', 'incomeBeforeTax']].values.tolist(),
                            financial_leverage = evaluator[['date', 'financial leverage']].values.tolist(),)

def stockEvaluator(holder,dates):
    import numpy as np
    evaluator = pd.DataFrame()
    # lock in date
    evaluator['date'] = dates
    evaluator['Date'] =pd.to_datetime(evaluator['date'])
    evaluator.sort_values(by=['Date'], ascending=False,inplace=True)
    evaluator['date']= evaluator['date'].apply(lambda x: datetime.datetime.combine(x, datetime.time()).timestamp()*1000)

    #-------- consider profitability ------------
    ## get profit margin ratio
    ## good ratio would be about 65%
    evaluator['gross profit margin'] = holder.loc['grossProfit']/holder.loc['totalRevenue']

    ## get ebit ratio
    evaluator['net profit margin'] = holder.loc['netIncomeFromContinuingOps']/holder.loc['totalRevenue']

    evaluator['roa'] = holder.loc['incomeBeforeTax']/holder.loc['totalAssets']

    #--------------- consider debt ---------------
    ## get gearing ratio
    evaluator['gearing'] = holder.loc['totalLiab']/holder.loc['totalStockholderEquity']

    ## get equity ratio
    evaluator['equity'] = holder.loc['totalStockholderEquity']/holder.loc['totalAssets']

        ## get debt asset ratio
    evaluator['debt asset'] = holder.loc['totalLiab']/holder.loc['totalAssets']

    #----------------- management ------------------
    evaluator['asset turnover'] = holder.loc['totalRevenue']/holder.loc['totalAssets']

    #----------------- investor ---------------------
    evaluator['roc'] = holder.loc['incomeBeforeTax']/(holder.loc['totalAssets']-holder.loc['totalLiab'])

    evaluator['roe'] = holder.loc['incomeBeforeTax']/holder.loc['totalStockholderEquity']

    #----------- raw value ----
    evaluator['totalRevenue'] = holder.loc['totalRevenue']/10**6
    evaluator['costOfRevenue'] = holder.loc['costOfRevenue']/10**6
    evaluator['grossProfit'] = holder.loc['grossProfit']/10**6
    evaluator['incomeBeforeTax'] = holder.loc['incomeBeforeTax']/10**6
    evaluator['netIncomeFromContinuingOps'] = holder.loc['netIncomeFromContinuingOps']

    evaluator['change in revenue'] = evaluator.sort_values(by=['Date'], ascending=True).T.loc['totalRevenue'].pct_change()
    evaluator['change net profit'] = evaluator.sort_values(by=['Date'], ascending=True).T.loc['incomeBeforeTax'].pct_change()
    evaluator['financial leverage'] = evaluator.T.loc['change net profit'].astype(float)/evaluator.T.loc['change in revenue'].astype(float)

    evaluator.replace([np.inf,-np.inf,np.nan], 0, inplace=True)
    print(evaluator[['change in revenue','change net profit','financial leverage','incomeBeforeTax']])
    evaluator.fillna(0, inplace=True)

    
    return evaluator
