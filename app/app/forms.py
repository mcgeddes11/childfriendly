# -*- encoding: utf-8 -*-
"""
Python Aplication Template
Licence: GPLv3
"""

from flask_wtf import Form
from wtforms.fields import StringField, PasswordField
from wtforms.validators import Required, DataRequired, NumberRange

class AddressAgeEntryForm(Form):
    address = StringField(label="address", validators=[DataRequired()],render_kw={"placeholder": "Enter your address..."})
    age = StringField(label="age", validators=[DataRequired(), NumberRange(1,18)],render_kw={"placeholder": "Child's age..."})


class LoginForm(Form):
    username = StringField(u'Username', validators = [DataRequired()])
    password = PasswordField(u'Password', validators = [DataRequired()])
