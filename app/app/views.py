# -*- encoding: utf-8 -*-
"""
Python Aplication Template
Licence: GPLv3
"""

from flask import url_for, redirect, render_template, flash, g, session, jsonify, request, abort
from flask_login import login_user, logout_user, current_user, login_required
from app import app, lm, geocoder, scoring_service, mongodb_service
from forms import LoginForm, AddressAgeEntryForm
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
    # Test retrieval based on geo-location
    co_ords = geocoder.geocode(address)
    census_data = mongodb_service.mg_get_near("census", co_ords.latitude, co_ords.longitude, 5000)
    crime_data = mongodb_service.mg_get_near("crime", co_ords.latitude, co_ords.longitude, 5000)
    school_data = mongodb_service.mg_get_near("school", co_ords.latitude, co_ords.longitude, 5000)
    data = {"address": address, "age": age, "census": census_data, "crime": crime_data, "school": school_data}
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
