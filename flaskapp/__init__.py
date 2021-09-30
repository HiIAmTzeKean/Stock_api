import os
from flask import Flask
from flask_wtf.csrf import CSRFProtect
import logging
from apscheduler.schedulers.background import BackgroundScheduler

app = Flask(__name__, instance_relative_config=True,
            template_folder='templates')


# ensure the instance folder exists
try:
    os.makedirs(app.instance_path)
except OSError:
    pass

logging.basicConfig(level=logging.ERROR,format='%(asctime)s %(levelname)s %(name)s %(threadName)s : %(message)s)')

# load config
app.config.from_object(os.environ['APP_SETTINGS'])
csrf = CSRFProtect(app)

# connect database to app
from flask_sqlalchemy import SQLAlchemy
db = SQLAlchemy(app)

from flask_migrate import Migrate
migrate = Migrate(app, db)

# start scheduler
scheduler = BackgroundScheduler()

# import models 
from flaskapp import models

from .shortSell import shortSell
app.register_blueprint(shortSell.shortSell_bp)

from .financials import financials
app.register_blueprint(financials.financials_bp)

from .charting import charting
app.register_blueprint(charting.charting_bp)

from .initialiser import initialiser
app.register_blueprint(initialiser.initialiser_bp)
app.add_url_rule('/', endpoint='initialiser.initialiserHome')
