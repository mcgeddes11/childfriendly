# -*- encoding: utf-8 -*-
"""
Python Aplication Template
Licence: GPLv3
"""

from flask import url_for, redirect, render_template, flash, g, session
from flask_login import login_user, logout_user, current_user, login_required
from app import app, lm
from forms import ExampleForm, LoginForm
from models import User

@app.route('/')
@app.route("/index")
def index():
    return render_template('index.html')

@app.route("/methodology")
def methodology():
    return render_template('index.html')

@app.route("/contact")
def contact():
    return render_template('index.html')



# === User login methods ===

@app.before_request
def before_request():
    g.user = current_user

@lm.user_loader
def load_user(id):
    return User.query.get(int(id))

@app.route('/login', methods = ['GET', 'POST'])
def login():
    if g.user is not None and g.user.is_authenticated():
        return redirect(url_for('index'))
    form = LoginForm()
    if form.validate_on_submit():
        login_user(g.user)

    return render_template('login.html',
        title = 'Sign In',
        form = form)

@app.route('/logouts')
def logout():
    logout_user()
    return redirect(url_for('index'))

# ====================
