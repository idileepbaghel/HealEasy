from flask import render_template, request, redirect, url_for, flash, session, Blueprint
from application.extensions import mysql
from datetime import datetime

pharm_details = Blueprint('pharm_details', __name__)

@pharm_details.route('/pharm_details', methods=['GET','POST'])
def details():
    # Get pharmacy id from session
    if 'user' not in session:
        flash('Please login first', 'error')
        return redirect(url_for('auth_bp.login'))
        
    pharmacy_id = session['user'].get('pharmacy_service_id')
    
    cur = mysql.connection.cursor()
    cur.execute("""SELECT * FROM pharmacy_service WHERE id = %s""", (pharmacy_id,))
    item = cur.fetchone()
    mysql.connection.commit()
    cur.close()
    
    if not item:
        flash('Pharmacy details not found', 'error')
        return redirect(url_for('auth_bp.dashboard'))
    
    return render_template('pharmacy_details.html', item=item)

@pharm_details.route('/edit_pharm_details/<int:id>', methods=['POST','GET'])
def edit_details(id):
    # Ensure user can only edit their own pharmacy
    if 'user' not in session:
        flash('Please login first', 'error')
        return redirect(url_for('auth_bp.login'))
        
    session_pharmacy_id = session['user'].get('pharmacy_service_id')
    if int(id) != int(session_pharmacy_id):
        flash('You can only edit your own pharmacy details', 'error')
        return redirect(url_for('pharm_details.details'))
    
    if request.method == 'POST':
        pharmacy_id = request.form['id']
        
        pharmacy_name = request.form['pharmacy_name']
        pharmacy_address = request.form['pharmacy_address']
        pharmacy_city = request.form['pharmacy_city']
        pharmacy_state = request.form['pharmacy_state']
        pharmacy_pincode = request.form['pharmacy_pincode']
        pharmacy_primary_name = request.form['pharmacy_primary_name']
        pharmacy_primary_number = request.form['pharmacy_primary_number']
        pharmacy_secondary_name = request.form['pharmacy_secondary_name']
        pharmacy_secondary_number = request.form['pharmacy_secondary_number']
        pharmacy_user_count = request.form['pharmacy_user_count']
        pharmacy_email = request.form['pharmacy_email']
        pharmacy_license_number = request.form['pharmacy_license_number']
        invoice_range = request.form['invoice_range']
        
        cur = mysql.connection.cursor()
        cur.execute("""UPDATE pharmacy_service 
            SET pharmacy_name=%s, pharmacy_address=%s, pharmacy_city=%s, pharmacy_state=%s, 
            pharmacy_pincode=%s, pharmacy_primary_name=%s, pharmacy_primary_number=%s, 
            pharmacy_secondary_name=%s, pharmacy_secondary_number=%s, pharmacy_user_count=%s, 
            pharmacy_email=%s, pharmacy_license_number=%s, invoice_range=%s
            WHERE id=%s
            """, (pharmacy_name, pharmacy_address, pharmacy_city, pharmacy_state,
                 pharmacy_pincode, pharmacy_primary_name, pharmacy_primary_number, 
                 pharmacy_secondary_name, pharmacy_secondary_number, pharmacy_user_count, 
                 pharmacy_email, pharmacy_license_number, invoice_range, pharmacy_id))
        mysql.connection.commit()
        cur.close()
        
        flash('Pharmacy details updated successfully.', 'success')
        return redirect(url_for('pharm_details.details'))
    
    # For GET request, fetch the pharmacy details
    cur = mysql.connection.cursor()
    cur.execute("""SELECT * FROM pharmacy_service WHERE id = %s""", (id,))
    item = cur.fetchone()
    cur.close()
    
    if item:
        return render_template('edit_pharmacy.html', item=item)
    else:
        flash('Pharmacy not found', 'danger')
        return redirect(url_for('pharm_details.details'))