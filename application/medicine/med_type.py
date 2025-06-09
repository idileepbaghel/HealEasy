from flask import render_template, request, redirect, url_for, flash, session, Blueprint
from application.extensions import mysql

med_bp = Blueprint('meds', __name__)

@med_bp.route('/meds', methods = ['GET', 'POST'])
def meds():
     cur = mysql.connection.cursor()

     if request.method == "GET":
        cur.execute("SELECT * FROM master_medicine_type")
        med = cur.fetchall()
        return render_template('medicine_type.html', data = med)
