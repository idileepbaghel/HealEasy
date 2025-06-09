from flask import Blueprint, render_template, request, redirect, url_for, flash, session, send_file
from application.extensions import mysql
from datetime import datetime
import io


lowstock = Blueprint('lowstock', __name__)

@lowstock.route('/low_stocks', methods=['GET', 'POST'])
def stocks():
    
    if 'user' not in session:
        flash('Please login first', 'error')
        return redirect(url_for('auth_bp.login'))
    
    cur = mysql.connection.cursor()
    pharmacy_id = session['user'].get('pharmacy_service_id')
    
    if request.method=='GET':
        cur.execute(
            """SELECT ps.*, mm.medicine_name
            FROM pharmacy_stock ps
            JOIN master_medicine mm ON ps.pharmacy_medicine_id = mm.id
            WHERE ps.pharmacy_id=%s 
            """, (pharmacy_id,))
        items = cur.fetchall()
        
        # Get all medicine names for dropdown
        cur.execute("SELECT id, medicine_name FROM master_medicine")
        med_names = cur.fetchall()
        
        return render_template('stock_report.html',
                              items=items,
                              med_names=med_names)
    
    return render_template('stock_report.html', items=items)
