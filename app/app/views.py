# -*- encoding: utf-8 -*-
"""
Python Aplication Template
Licence: GPLv3
"""

from flask import url_for, redirect, render_template, g, request
from flask_login import logout_user, current_user

from app import app, lm, geocoder
from app.services import scoring_service
from forms import LoginForm
from models import User


@app.route('/')
@app.route("/index")
def index():
    msg = ""
    return render_template('index.html', msg=msg)

@app.route("/methodology")
def methodology():
    return render_template('methodology.html')

@app.route("/contact")
def contact():
    return render_template('contact.html')

@app.route("/compute_friendliness", methods=["GET","POST"])
def compute_friendliness():
    msg = ""
    address = request.args["address"]
    age = request.args["age"]
    # Use google geolocator api to get the lat/long
    co_ords = geocoder.geocode(address)
    # Score based on location
    score_data = scoring_service.compute_score(co_ords.latitude, co_ords.longitude, int(age))
    data = {"address": address, "age": age, "score_data": score_data}
    return render_template("results.html", msg=msg, data=data)


# === User login methods ===

@app.before_request
def before_request():
    g.user = current_user

@lm.user_loader
def load_user(id):
    return User.query.get(int(id))

@app.route('/login/', methods = ['GET', 'POST'])
def login():
    if g.user is not None and g.user.is_authenticated:
        return redirect(url_for('index'))
    form = LoginForm()
    if form.validate_on_submit():
        # Currently we have no users (and no database!), so return message saying so
        msg = "User not found!"
        # login_user(g.user)
        return render_template('login.html',title = 'Sign In',form = form, msg=msg)
    else:
        return render_template('login.html', title='Sign In', form=form, msg="")

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))

# ====================
