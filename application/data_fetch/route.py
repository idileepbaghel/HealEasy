from flask import render_template, request, redirect, url_for, flash, session, Blueprint
from application.extensions import mysql

data_fetch = Blueprint('data_fetch', __name__)

@data_fetch.route('/fetch',methods=['GET','POST'])
def fetch():
    cur= mysql.connection.cursor()
    
    
    cur.execute("SELECT * FROM master_medicine_unit")
    data = cur.fetchall()
    return render_template('medicine_unit.html', data=data)


# add medicines


@data_fetch.route('/add',methods=['GET','POST'])
def add():

    if 'user' not in session:
        flash('Please login first', 'error')
        return redirect(url_for('auth_bp.login'))

    cur=mysql.connection.cursor()
    if request.method=='POST':
        unitname=request.form['medname']
        shname=request.form['shortname']

        cur.execute("""
            SELECT * FROM master_medicine_unit 
            WHERE LOWER(unit_name) = LOWER(%s) 
            OR LOWER(unit_short_name) = LOWER(%s)
        """, (unitname, shname))
        existing_unit = cur.fetchone()
        
        if existing_unit:
            flash("Can't add duplicate medicine unit or short name", "danger")
            return redirect(url_for('data_fetch.fetch'))

        cur=cur.execute("INSERT INTO master_medicine_unit (unit_name,unit_short_name) VALUES (%s, %s)", (unitname, shname,))

        flash(f"{unitname} added successfully!",'success')
        
        mysql.connection.commit()
        
        return redirect(url_for('data_fetch.fetch'))
        