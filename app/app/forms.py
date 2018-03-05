# -*- encoding: utf-8 -*-
"""
Python Aplication Template
Licence: GPLv3
"""

from flask_wtf import Form
from wtforms.fields import TextField, TextAreaField, DateTimeField, PasswordField
from wtforms.validators import Required


class ExampleForm(Form):
    title = TextField(u'Título', validators = [Required()])
    content = TextAreaField(u'Conteúdo')
    date = DateTimeField(u'Data', format='%d/%m/%Y %H:%M')
    #recaptcha = RecaptchaField(u'Recaptcha')


class LoginForm(Form):
    user = TextField(u'Usuário', validators = [Required()])
    password = PasswordField(u'Senha', validators = [Required()])
