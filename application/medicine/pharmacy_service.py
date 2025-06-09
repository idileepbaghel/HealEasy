from flask import Flask, render_template, request, redirect, url_for, Blueprint
from datetime import datetime
from application.extensions import mysql

pharmacy_service = Blueprint('pharmacy_service',__name__)

@pharmacy_service.route('/service', methods=['GET','POST'])
def service():
    cur = mysql.connection.cursor()

    cur.execute("SELECT * FROM pharmacy_service where ")

    pharmacies = cur.fetchall()

    return render_template('pharmacy_service.html', pharmacies = pharmacies)    
