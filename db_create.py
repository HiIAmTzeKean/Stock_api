# for heroku production launch
from flaskapp import db

db.create_all()