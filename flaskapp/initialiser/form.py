from flask_wtf import FlaskForm
from wtforms import BooleanField, StringField, validators, SelectField, SubmitField, FieldList, FormField, IntegerField
from wtforms.fields.html5 import DateField
from wtforms.validators import DataRequired, InputRequired, Optional

class formTickerEdit(FlaskForm):
    ticker = StringField(label='Ticker', validators=[DataRequired()])
    name = StringField(label='Name', validators=[DataRequired()])
    website = StringField(label='Website', validators=[DataRequired()])
    submit = SubmitField('Submit')