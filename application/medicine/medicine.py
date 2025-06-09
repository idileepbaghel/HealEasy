from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from application.extensions import mysql
from datetime import datetime

medicine_bp = Blueprint('medicine_bp', __name__)

@medicine_bp.route('/medicine', methods=['GET', 'POST'])
def medicine():
    cur = mysql.connection.cursor()

    if 'user' not in session:
        flash('Please login first', 'error')
        return redirect(url_for('auth_bp.login')) 

    if request.method == 'POST':
        type = request.form['type']
        description = request.form['description']
        added_by = session['user']['full_name']

        cur.execute("SELECT * FROM master_medicine_type WHERE LOWER(type_name) = LOWER(%s)", (type,))
        existing_medicine = cur.fetchone()
        
        if existing_medicine:
            flash("Can't add duplicate medicine's type", "danger")
            return redirect(url_for('meds.meds'))
        
        cur.execute("""
                INSERT INTO master_medicine_type 
                (type_name, description, added_by)
                VALUES (%s, %s, %s)
            """, (type, description, added_by))
            
        mysql.connection.commit()
            
        flash('Medicine Type added successfully!', 'success')
        return redirect(url_for('meds.meds'))

    
