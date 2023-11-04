from flask import Flask, render_template, request, url_for, flash, redirect, abort, jsonify, session
import plotly.graph_objs as go

from authlib.integrations.flask_client import OAuth
from flask_session import Session

import json
import os
import sqlite3
import requests

import psycopg2

from utilities import utils

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get("SECRET_KEY", os.urandom(12))
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"

Session(app)
oauth = OAuth(app)

@app.route('/', methods = ('GET', 'POST'))
@app.route('/home', methods = ('GET', 'POST'))
def index():
	return utils.index_page()