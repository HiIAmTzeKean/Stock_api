from flask_wtf import FlaskForm
from wtforms import BooleanField, StringField, validators, SelectField, SubmitField, FieldList, FormField, IntegerField
from wtforms.fields.html5 import DateField
from wtforms.validators import DataRequired, InputRequired, Optional

class formTickerChoose(FlaskForm):
    ticker = SelectField(label='Ticker', choices='', validators=[DataRequired()])
    submit = SubmitField('Submit')