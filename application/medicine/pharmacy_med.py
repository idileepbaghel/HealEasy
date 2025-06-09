from flask import render_template, request, redirect, url_for, flash, session, Blueprint
from application.extensions import mysql
from datetime import datetime

pharm_name = Blueprint('pharm_name', __name__)

@pharm_name.route('/medicines', methods=['GET'])
def med_details():
    if request.method == "GET":

        if 'user' not in session:
            flash('Please login first', 'error')
            return redirect(url_for('auth_bp.login'))
        
        # Get medicine data with joins to related tables
        cur = mysql.connection.cursor()

        pharmacy_id = session['user'].get('pharmacy_service_id')

        cur.execute("""
            SELECT m.id, m.medicine_name, m.generic_name, m.composition, m.strength, 
                   t.type_name, u.unit_short_name, man.manufacturer_name, m.type_id, 
                   m.unit_id, m.manufacturer_id
            FROM pharmacy_medicine m
            LEFT JOIN master_medicine_type t ON m.type_id = t.id
            LEFT JOIN master_medicine_unit u ON m.unit_id = u.id
            LEFT JOIN master_medicine_manufacturer man ON m.manufacturer_id = man.id
            WHERE m.pharmacy_id=%s
            ORDER BY m.id DESC
            
        """, (pharmacy_id,))
        data = cur.fetchall()
        
        # Get medicine types for dropdown
        cur.execute("SELECT * FROM master_medicine_type")
        med_types = cur.fetchall()
        
        # Get medicine units for dropdown
        cur.execute("SELECT * FROM master_medicine_unit")
        med_units = cur.fetchall()
        
        # Get manufacturers for dropdown
        cur.execute("SELECT * FROM master_medicine_manufacturer")
        manufacturers = cur.fetchall()
        
        return render_template('pharmacy_medicine.html', data=data, med_types=med_types, 
                              med_units=med_units, manu=manufacturers)

@pharm_name.route('/medicines', methods=['POST'])
def add_medicine():
    # Add new medicine
    if request.method == "POST":
        pharmacy_id = request.form['pharmacy_id']
        medicine_name = request.form['medsname']
        generic_name = request.form['genericname']
        composition = request.form['composition']
        strength = request.form['strenght']  # Note: keeping the typo as it exists in the form
        type_id = request.form['type_id']
        unit_id = request.form['unit_id']
        manufacturer_id = request.form['manufacturer_id']
        
        # Get user ID from session
        added_by = session.get('user_id', 1)  # Default to 1 if not in session
        current_time = datetime.now()
        
        cur = mysql.connection.cursor()
        
        # Check if medicine already exists in pharmacy's medicine list
        cur.execute("""
            SELECT id FROM pharmacy_medicine 
            WHERE LOWER(medicine_name) = LOWER(%s) AND pharmacy_id = %s
        """, (medicine_name, pharmacy_id))
        
        if cur.fetchone():
            flash('Cannot add duplicate medicine. A medicine with this name already exists.', 'warning')
            return redirect(url_for('pharm_name.med_details'))
        
        # If no duplicate found, insert the new medicine
        cur.execute("""
            INSERT INTO pharmacy_medicine 
            (pharmacy_id, medicine_name, generic_name, composition, strength, type_id, unit_id, manufacturer_id, added_by, added_date) 
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, 
            (pharmacy_id, medicine_name, generic_name, composition, strength, type_id, unit_id, manufacturer_id, added_by, current_time))
        mysql.connection.commit()
        
        flash('Medicine added successfully', 'success')
        return redirect(url_for('pharm_name.med_details'))

@pharm_name.route('/edit-medicine/<int:id>', methods=['POST'])
def edit_mednames(id):
    if request.method == "POST":
        pharmacy_id = request.form['pharmacy_id']
        medicine_name = request.form['medicine_name']
        generic_name = request.form['genericname']
        composition = request.form['composition']
        strength = request.form['strenght']  # Note: keeping the typo as it exists in the form
        type_id = request.form['type_id']
        unit_id = request.form['unit_id']
        manufacturer_id = request.form['manufacturer_id']
        
        # Get user ID from session
        updated_by = session.get('user_id', 1)  # Default to 1 if not in session
        current_time = datetime.now()
        
        cur = mysql.connection.cursor()
        
        # Check if another medicine with same name exists (excluding current medicine)
        cur.execute("""
            SELECT id FROM pharmacy_medicine 
            WHERE LOWER(medicine_name) = LOWER(%s) 
            AND pharmacy_id = %s 
            AND id != %s
        """, (medicine_name, pharmacy_id, id))
        
        if cur.fetchone():
            flash('Cannot update to duplicate medicine name. Another medicine with this name already exists.', 'warning')
            return redirect(url_for('pharm_name.med_details'))
            
        # If no duplicate found, update the medicine
        cur.execute("""
            UPDATE pharmacy_medicine 
            SET pharmacy_id =%s, medicine_name = %s, generic_name = %s, composition = %s, strength = %s,
                type_id = %s, unit_id = %s, manufacturer_id = %s, 
                updated_by = %s, updated_date = %s 
            WHERE id = %s
            """, 
            (pharmacy_id, medicine_name, generic_name, composition, strength, type_id, unit_id, 
             manufacturer_id, updated_by, current_time, id))
        mysql.connection.commit()
        
        flash('Medicine updated successfully', 'success')
        return redirect(url_for('pharm_name.med_details'))

@pharm_name.route('/delete-medicine/<int:id>/<string:medicine_name>')
def delete_mednames(id, medicine_name):
    cur = mysql.connection.cursor()
    
    # Delete the medicine
    cur.execute("DELETE FROM pharmacy_medicine WHERE id = %s", (id,))
    mysql.connection.commit()
    
    flash(f'Medicine "{medicine_name}" deleted successfully', 'success')
    return redirect(url_for('pharm_name.med_details'))



# Add these routes to your pharm_name Blueprint

@pharm_name.route('/select-master-medicines', methods=['GET'])
def select_master_medicines():
    cur = mysql.connection.cursor()
    
    # Get all master medicines
    cur.execute("""
        SELECT m.*, t.type_name, u.unit_short_name, man.manufacturer_name
        FROM master_medicine m
        LEFT JOIN master_medicine_type t ON m.type_id = t.id
        LEFT JOIN master_medicine_unit u ON m.unit_id = u.id
        LEFT JOIN master_medicine_manufacturer man ON m.manufacturer_id = man.id
        ORDER BY m.medicine_name ASC
    """)
    master_medicines = cur.fetchall()
    
    # Get list of already selected medicines (by medicine_name)
    cur.execute("""
        SELECT medicine_name 
        FROM pharmacy_medicine
    """)
    selected_medicines = {item['medicine_name']: True for item in cur.fetchall()}
    
    return render_template('master_medicine_select.html', 
                          master_medicines=master_medicines,
                          selected_medicines=selected_medicines)

@pharm_name.route('/add-from-master', methods=['POST'])
def add_from_master():
    """
    Add selected medicines with all their fields to pharmacy_medicine
    """
    if request.method == "POST":
        selected_medicines = request.form.getlist('selected_medicines')
        
        if not selected_medicines:
            flash('Please select at least one medicine', 'warning')
            return redirect(url_for('pharm_name.select_master_medicines'))
        
        cur = mysql.connection.cursor()
        success_count = 0
        already_exists = 0
        added_by = session.get('user_id', 1)
        pharmacy_id = session['user'].get('pharmacy_service_id')  # Get pharmacy_id from session
        current_time = datetime.now()
        
        for med_id in selected_medicines:
            # Check if already exists for this pharmacy
            cur.execute("""
                SELECT id FROM pharmacy_medicine 
                WHERE medicine_name = (SELECT medicine_name FROM master_medicine WHERE id = %s)
                AND pharmacy_id = %s
            """, (med_id, pharmacy_id))
            
            if cur.fetchone():
                already_exists += 1
                continue
            
            cur.execute("""
                INSERT INTO pharmacy_medicine 
                (medicine_name, generic_name, composition, strength,
                 type_id, unit_id, manufacturer_id, added_by, added_date, pharmacy_id)
                SELECT 
                    medicine_name, generic_name, composition, strength,
                    type_id, unit_id, manufacturer_id, %s, %s, %s
                FROM master_medicine 
                WHERE id = %s
            """, (added_by, current_time, pharmacy_id, med_id))
            
            success_count += 1
        
        mysql.connection.commit()
        
        if success_count > 0:
            flash(f'{success_count} medicine(s) added successfully', 'success')
        if already_exists > 0:
            flash(f'{already_exists} medicine(s) already exist in your list', 'warning')
            
        return redirect(url_for('pharm_name.med_details'))