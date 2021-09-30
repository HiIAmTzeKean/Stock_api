from flaskapp import db, scheduler
from flaskapp.models import stockTicker, stockQuaterlyResults,stockYearlyResults
from sqlalchemy.exc import IntegrityError,InvalidRequestError,DataError

def getResult(ticker, period='Quarterly'):
    import requests
    from bs4 import BeautifulSoup
    import re
    import pandas as pd
    import json

    ## get page url content
    url = "https://sg.finance.yahoo.com/quote/{}/financials".format(ticker)
    page = requests.get(url, headers={'User-Agent': 'Custom'})
    soup = BeautifulSoup(page.text,'html.parser')

    ## get the first match from re
    soup_script = soup.find("script",text=re.compile("root.App.main"))
    ## remove "root.App.main = " from the match
    json_script = json.loads(re.search("root.App.main\s+=\s+(\{.*\})",soup_script.string)[0][16:])
    summary = json_script.get('context').get('dispatcher').get('stores').get('QuoteSummaryStore')

    ## ------ determine which key to use ---------
    if period=='Quarterly':
        mykeys = [['incomeStatement','incomeStatementHistoryQuarterly'],
                ['balanceSheet','balanceSheetHistoryQuarterly'],
                ['cashFlow','cashflowStatementHistoryQuarterly']]
    else:
        mykeys = [['incomeStatement','incomeStatementHistory'],
                ['balanceSheet','balanceSheetHistory'],
                ['cashFlow','cashflowStatementHistory']]

    
    ## iternate through the 3 sheets and append it into a dict
    holder = dict()
    for name,item in mykeys:
        holder[name] = extractData(summary.get(item))
        
        ## pop keys that do not fit the table col num
        for key in list(holder[name].keys()):
            if len(holder[name][key])!=4:
                holder[name].pop(key)
                continue

        ## convert data to dataframe 
        holder[name] = pd.DataFrame(holder[name]).set_index('endDate')
        holder[name].sort_values('endDate',ascending=True,inplace=True)

    holder = holder['cashFlow'].merge(holder['balanceSheet'],on='endDate').merge(holder['incomeStatement'],on='endDate')
    return holder


def extractData(statement):
    from collections import defaultdict
    holder = defaultdict(list)
    keyType = list(statement.keys())[0]
    for i in statement.get(keyType):
        for j in i:
            if j =='endDate':
                holder[j].append(i.get(j).get('fmt'))
                continue
            try:
                holder[j].append(i.get(j).get('raw'))
            except:
                pass
    return holder


def insertResult(records, ticker, period='Quarterly'):
    ## insert only missing records
    ## query for the exisiting dates
    if period == 'Quarterly':
        last_date = db.session.query(stockQuaterlyResults.date)\
                .filter_by(ticker_fk=ticker)\
                .order_by(stockQuaterlyResults.date.desc()).all()
    else:
        last_date = db.session.query(stockYearlyResults.date)\
                .filter_by(ticker_fk=ticker)\
                .order_by(stockYearlyResults.date.desc()).all()
    
    #------------- convert date to string --------------
    if last_date:
        last_date = [d.strftime("%Y-%m-%d") for d in list(list(zip(*last_date))[0])]

    ## for match the dates in last_date to records
    for currentDate in records.index:
        if currentDate in last_date:
            continue
        #------------------- do insertion of record here ----------------
        try:
            if period == 'Quarterly':
                db.session.add(stockQuaterlyResults(ticker,currentDate,records.loc[records.index == currentDate].to_dict('record')[0]))
            else:
                db.session.add(stockYearlyResults(ticker,currentDate,records.loc[records.index == currentDate].to_dict('record')[0]))
            db.session.commit()
            print(currentDate,'was not in the db')
        except (IntegrityError,InvalidRequestError,DataError) as e:
            print(currentDate,'is already in the db')
            pass
        #-----------------------------------------------------------------
    return


def updateAllResultTable(ticker,period):
    records = getResult(ticker,period)
    insertResult(records, ticker,period)
    return