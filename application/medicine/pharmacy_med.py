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
        
        cur = mysql.connection.cursor()        
        pharmacy_id = session['user'].get('pharmacy_service_id')        
        cur.execute("""
            SELECT m.id, m.medicine_name, m.generic_name, m.composition, m.strength, 
                   t.type_name, u.unit_short_name, man.manufacturer_name, m.type_id, 
                   m.unit_id, m.manufacturer_id, m.pharmacy_id,
                   ps.id as stock_id, ps.quantity, ps.batch_number, ps.expiry_date, 
                   ps.purchase_price, ps.selling_price,
                   pr.id as ratelist_id, pr.amount, pr.quantity_per_pack, pr.discount, 
                   pr.CGST, pr.SGST
            FROM pharmacy_medicine m
            LEFT JOIN master_medicine_type t ON m.type_id = t.id
            LEFT JOIN master_medicine_unit u ON m.unit_id = u.id
            LEFT JOIN master_medicine_manufacturer man ON m.manufacturer_id = man.id
            LEFT JOIN pharmacy_stock ps ON m.id = ps.pharmacy_medicine_id AND ps.pharmacy_id = %s
            LEFT JOIN pharmacy_ratelist pr ON m.id = pr.pharmacy_medicine_id AND pr.pharmacy_id = %s
            WHERE m.pharmacy_id IN (0, %s)
            ORDER BY m.id DESC
            
        """, (pharmacy_id, pharmacy_id, pharmacy_id))
        data = cur.fetchall()
        
        
        cur.execute("SELECT * FROM master_medicine_type")
        med_types = cur.fetchall()
        
        
        cur.execute("SELECT * FROM master_medicine_unit")
        med_units = cur.fetchall()
        
        
        cur.execute("SELECT * FROM master_medicine_manufacturer")
        manufacturers = cur.fetchall()
        
        return render_template('pharmacy_medicine.html', data=data, med_types=med_types, 
                              med_units=med_units, manu=manufacturers)

@pharm_name.route('/medicines', methods=['POST'])
def add_medicine():
    if request.method == "POST":
        pharmacy_id = request.form['pharmacy_id']
        
        
        medicine_name = request.form['medsname']
        generic_name = request.form['genericname']
        composition = request.form['composition']
        strength = request.form['strenght'] 
        type_id = request.form['type_id']
        unit_id = request.form['unit_id']
        manufacturer_id = request.form['manufacturer_id']
        
        
        stock_quantity = request.form.get('stock_quantity', '')
        batch_number = request.form.get('batch_number', '')
        expiry_date = request.form.get('expiry_date', '')
        purchase_price = request.form.get('purchase_price', '')
        selling_price = request.form.get('selling_price', '')
        
        
        ratelist_amount = request.form.get('ratelist_amount', '')
        quantity_per_pack = request.form.get('quantity_per_pack', '')
        discount = request.form.get('discount', '')
        cgst = request.form.get('CGST', '')
        sgst = request.form.get('SGST', '')
        
        
        added_by = session.get('user_id', 1) 
        current_time = datetime.now()
        
        cur = mysql.connection.cursor()        
        try:
            print(f"Adding medicine: {medicine_name}, pharmacy_id: {pharmacy_id}")
            print(f"Stock details - Quantity: {stock_quantity}, Batch: {batch_number}, Expiry: {expiry_date}")
            print(f"Ratelist details - Amount: {ratelist_amount}, Qty/Pack: {quantity_per_pack}")
            
            cur.execute("""
                SELECT id FROM pharmacy_medicine 
                WHERE LOWER(medicine_name) = LOWER(%s) AND pharmacy_id = %s
            """, (medicine_name, pharmacy_id))
            
            if cur.fetchone():
                flash('Cannot add duplicate medicine. A medicine with this name already exists.', 'warning')
                return redirect(url_for('pharm_name.med_details'))
            
            # Insert medicine details
            print("Inserting medicine details")
            cur.execute("""
                INSERT INTO pharmacy_medicine 
                (pharmacy_id, medicine_name, generic_name, composition, strength, type_id, unit_id, manufacturer_id, added_by, added_date) 
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, 
                (pharmacy_id, medicine_name, generic_name, composition, strength, type_id, unit_id, manufacturer_id, added_by, current_time))
            
            medicine_id = cur.lastrowid
            print(f"Medicine inserted with ID: {medicine_id}")
            
            # Insert stock details if provided
            if any([stock_quantity, batch_number, expiry_date, purchase_price, selling_price]):
                print("Inserting stock details")
                cur.execute("""
                    INSERT INTO pharmacy_stock 
                    (pharmacy_id, pharmacy_medicine_id, quantity, batch_number, expiry_date, purchase_price, selling_price) 
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (pharmacy_id, medicine_id, stock_quantity or 0, batch_number, expiry_date, 
                      purchase_price or 0, selling_price or 0))
                print(f"Stock insert rows affected: {cur.rowcount}")
            
            # Insert ratelist details if provided
            if any([ratelist_amount, quantity_per_pack, discount, cgst, sgst]):
                print("Inserting ratelist details")
                cur.execute("""
                    INSERT INTO pharmacy_ratelist 
                    (pharmacy_id, pharmacy_medicine_id, ratelist_name, amount, quantity_per_pack, discount, CGST, SGST) 
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """, (pharmacy_id, medicine_id, medicine_name, ratelist_amount or 0, quantity_per_pack or 1,
                      discount or 0, cgst or 0, sgst or 0))
                print(f"Ratelist insert rows affected: {cur.rowcount}")
            
            mysql.connection.commit()
            flash('Medicine, stock, and ratelist added successfully', 'success')
            
        except Exception as e:
            mysql.connection.rollback()
            flash(f'Error adding records: {str(e)}', 'danger')
        
        return redirect(url_for('pharm_name.med_details'))

@pharm_name.route('/edit-medicine/<int:id>', methods=['POST'])
def edit_mednames(id):
    if request.method == "POST":
        pharmacy_id = request.form['pharmacy_id']
        medicine_name = request.form['medicine_name']
        generic_name = request.form['genericname']
        composition = request.form['composition']
        strength = request.form['strenght']  
        type_id = request.form['type_id']
        unit_id = request.form['unit_id']
        manufacturer_id = request.form['manufacturer_id']
        
        updated_by = session.get('user_id', 1)  
        current_time = datetime.now()
        cur = mysql.connection.cursor()
        
        cur.execute("""
            SELECT id FROM pharmacy_medicine 
            WHERE LOWER(medicine_name) = LOWER(%s) 
            AND pharmacy_id IN (0, %s) 
            AND id != %s
        """, (medicine_name, pharmacy_id, id))
        
        if cur.fetchone():
            flash('Cannot update to duplicate medicine name. Another medicine with this name already exists.', 'warning')
            return redirect(url_for('pharm_name.med_details'))
            
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
    
    
    cur.execute("DELETE FROM pharmacy_medicine WHERE id = %s", (id,))
    mysql.connection.commit()
    
    flash(f'Medicine "{medicine_name}" deleted successfully', 'success')
    return redirect(url_for('pharm_name.med_details'))





@pharm_name.route('/select-master-medicines', methods=['GET'])
def select_master_medicines():
    cur = mysql.connection.cursor()
    
    
    cur.execute("""
        SELECT m.*, t.type_name, u.unit_short_name, man.manufacturer_name
        FROM master_medicine m
        LEFT JOIN master_medicine_type t ON m.type_id = t.id
        LEFT JOIN master_medicine_unit u ON m.unit_id = u.id
        LEFT JOIN master_medicine_manufacturer man ON m.manufacturer_id = man.id
        ORDER BY m.medicine_name ASC
    """)
    master_medicines = cur.fetchall()
    
    
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
    Add selected medicines with all their fields to pharmacy_medicine from master_medicine
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
        pharmacy_id = session['user'].get('pharmacy_service_id') 
        current_time = datetime.now()
        
        for med_id in selected_medicines:
            
            cur.execute("""
                SELECT id FROM pharmacy_medicine 
                WHERE medicine_name = (SELECT medicine_name FROM master_medicine WHERE id = %s)
                AND pharmacy_id IN (0, %s)
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
                    type_id, unit_id, manufacturer_id, %s, %s, 0
                FROM master_medicine 
                WHERE id = %s
            """, (added_by, current_time, med_id))
            
            success_count += 1
        
        mysql.connection.commit()
        
        if success_count > 0:
            flash(f'{success_count} medicine(s) added successfully', 'success')
        if already_exists > 0:
            flash(f'{already_exists} medicine(s) already exist in your list', 'warning')
            
        return redirect(url_for('pharm_name.med_details'))



@pharm_name.route('/edit-medicine-combined/<int:id>', methods=['POST'])
def edit_medicine_combined(id):

    if request.method == "POST":
        
        pharmacy_id = session['user'].get('pharmacy_service_id')
        medicine_name = request.form['medicine_name']
        generic_name = request.form['genericname']
        composition = request.form['composition']
        strength = request.form['strenght'] 
        type_id = request.form['type_id']
        unit_id = request.form['unit_id']
        manufacturer_id = request.form['manufacturer_id']
        

        stock_quantity = request.form.get('stock_quantity', '')
        print(stock_quantity,'baghel')
        batch_number = request.form.get('batch_number', '')
        expiry_date = request.form.get('expiry_date', '')
        purchase_price = request.form.get('purchase_price', '')
        selling_price = request.form.get('selling_price', '')
        
        
        ratelist_amount = request.form.get('ratelist_amount', '')
        quantity_per_pack = request.form.get('quantity_per_pack', '')
        discount = request.form.get('discount', '')
        cgst = request.form.get('CGST', '')
        sgst = request.form.get('SGST', '')
        
        
        updated_by = session.get('user_id', 1)  
        current_time = datetime.now()
        
        cur = mysql.connection.cursor()
        
        try:
            
            cur.execute("""
                SELECT id FROM pharmacy_medicine 
                WHERE LOWER(medicine_name) = LOWER(%s) 
                AND pharmacy_id = %s 
                AND id != %s
            """, (medicine_name, pharmacy_id, id))
            
            if cur.fetchone():
                flash('Cannot update to duplicate medicine name. Another medicine with this name already exists.', 'warning')
                return redirect(url_for('pharm_name.med_details'))
            

            cur.execute("""
                UPDATE pharmacy_medicine 
                SET pharmacy_id = %s, medicine_name = %s, generic_name = %s, composition = %s, strength = %s,
                    type_id = %s, unit_id = %s, manufacturer_id = %s, 
                    updated_by = %s, updated_date = %s 
                WHERE id = %s
                """,                
                (pharmacy_id, medicine_name, generic_name, composition, strength, type_id, unit_id, 
                 manufacturer_id, updated_by, current_time, id))
            
            # Handle stock updates/inserts
            cur.execute("""
                SELECT id FROM pharmacy_stock 
                WHERE pharmacy_medicine_id = %s AND pharmacy_id = %s
            """, (id, pharmacy_id))
            
            stock_record = cur.fetchone()
            
            if stock_record:
                # Update existing stock record
                print("Updating existing stock record")
                cur.execute("""
                    UPDATE pharmacy_stock 
                    SET quantity = %s, batch_number = %s, expiry_date = %s, 
                        purchase_price = %s, selling_price = %s
                    WHERE pharmacy_medicine_id = %s AND pharmacy_id = %s
                """, (stock_quantity or 0, batch_number, expiry_date, 
                        purchase_price or 0, selling_price or 0, id, pharmacy_id))
                print(f"Stock update rows affected: {cur.rowcount}")
            else:
                # Insert new stock record if any stock data provided
                if any([stock_quantity, batch_number, expiry_date, purchase_price, selling_price]):
                    print("Inserting new stock record")
                    cur.execute("""
                        INSERT INTO pharmacy_stock 
                        (pharmacy_id, pharmacy_medicine_id, quantity, batch_number, expiry_date, purchase_price, selling_price) 
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """, (pharmacy_id, id, stock_quantity or 0, batch_number, expiry_date, 
                          purchase_price or 0, selling_price or 0))
                    print(f"Stock insert rows affected: {cur.rowcount}")
            
            mysql.connection.commit()
            # Handle ratelist updates/inserts
            cur.execute("""
                SELECT id FROM pharmacy_ratelist 
                WHERE pharmacy_medicine_id = %s AND pharmacy_id = %s
            """, (id, pharmacy_id))
            
            ratelist_record = cur.fetchone()
            
            if ratelist_record:
                # Update existing ratelist record
                print("Updating existing ratelist record")
                print(id, pharmacy_id, quantity_per_pack)
                cur.execute("""
                    UPDATE pharmacy_ratelist 
                    SET ratelist_name = %s, amount = %s, quantity_per_pack = %s, 
                        discount = %s, CGST = %s, SGST = %s
                    WHERE pharmacy_medicine_id = %s AND pharmacy_id = %s
                """, (medicine_name, ratelist_amount or 0, quantity_per_pack or 1,
                      discount or 0, cgst or 0, sgst or 0, id, pharmacy_id))
                print(f"Ratelist update rows affected: {cur.rowcount}")

                print(quantity_per_pack, pharmacy_id)
            else:
                # Insert new ratelist record if any ratelist data provided
                if any([ratelist_amount, quantity_per_pack, discount, cgst, sgst]):
                    print("Inserting new ratelist record")
                    cur.execute("""
                        INSERT INTO pharmacy_ratelist 
                        (pharmacy_id, pharmacy_medicine_id, ratelist_name, amount, quantity_per_pack, discount, CGST, SGST) 
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """, (pharmacy_id, id, medicine_name, ratelist_amount or 0, quantity_per_pack or 1,
                          discount or 0, cgst or 0, sgst or 0))
                    print(f"Ratelist insert rows affected: {cur.rowcount}")
            
            mysql.connection.commit()
            flash('Medicine, stock, and ratelist updated successfully', 'success')
            
        except Exception as e:
            mysql.connection.rollback()
            flash(f'Error updating records: {str(e)}', 'danger')
        
        return redirect(url_for('pharm_name.med_details'))

@pharm_name.route('/view-medicine-details/<int:medicine_id>', methods=['GET'])
def view_medicine_details(medicine_id):
    """Get stock and ratelist details for a specific medicine"""
    if 'user' not in session:
        flash('Please login first', 'error')
        return redirect(url_for('auth_bp.login'))
    
    cur = mysql.connection.cursor()
    pharmacy_id = session['user'].get('pharmacy_service_id')
    
    
    cur.execute("""
        SELECT ps.*, pm.medicine_name
        FROM pharmacy_stock ps
        JOIN pharmacy_medicine pm ON ps.pharmacy_medicine_id = pm.id
        WHERE ps.pharmacy_medicine_id = %s AND ps.pharmacy_id = %s
    """, (medicine_id, pharmacy_id))
    stock_data = cur.fetchall()
    
    cur.execute("""
        SELECT pr.*, pm.medicine_name
        FROM pharmacy_ratelist pr
        JOIN pharmacy_medicine pm ON pr.pharmacy_medicine_id = pm.id
        WHERE pr.pharmacy_medicine_id = %s AND pr.pharmacy_id = %s
    """, (medicine_id, pharmacy_id))
    ratelist_data = cur.fetchall()
    
    cur.close()
    
    from flask import jsonify
    return jsonify({
        'success': True,
        'stock_data': stock_data,
        'ratelist_data': ratelist_data
    })

@pharm_name.route('/medicine-details-page/<int:medicine_id>', methods=['GET'])
def medicine_details_page(medicine_id):
    """Display medicine details in a separate page with stock and ratelist tables"""
    if 'user' not in session:
        flash('Please login first', 'error')
        return redirect(url_for('auth_bp.login'))
    
    cur = mysql.connection.cursor()
    pharmacy_id = session['user'].get('pharmacy_service_id')
    
    # Get medicine basic details
    cur.execute("""
        SELECT m.*, t.type_name, u.unit_short_name, man.manufacturer_name
        FROM pharmacy_medicine m
        LEFT JOIN master_medicine_type t ON m.type_id = t.id
        LEFT JOIN master_medicine_unit u ON m.unit_id = u.id
        LEFT JOIN master_medicine_manufacturer man ON m.manufacturer_id = man.id
        WHERE m.id = %s AND m.pharmacy_id IN (0, %s)    """, 
        (medicine_id, pharmacy_id))
    medicine = cur.fetchone()
    
    if not medicine:
        flash('Medicine not found', 'error')
        return redirect(url_for('pharm_name.med_details'))
    
    # Get stock details
    cur.execute("""
        SELECT ps.*, pm.medicine_name
        FROM pharmacy_stock ps
        JOIN pharmacy_medicine pm ON ps.pharmacy_medicine_id = pm.id
        WHERE ps.pharmacy_medicine_id = %s AND ps.pharmacy_id = %s
        ORDER BY ps.expiry_date ASC
    """, (medicine_id, pharmacy_id))
    stock_data = cur.fetchall()
    
    # Get ratelist details
    cur.execute("""
        SELECT pr.*, pm.medicine_name
        FROM pharmacy_ratelist pr
        JOIN pharmacy_medicine pm ON pr.pharmacy_medicine_id = pm.id
        WHERE pr.pharmacy_medicine_id = %s AND pr.pharmacy_id = %s
        ORDER BY pr.ratelist_name ASC
    """, (medicine_id, pharmacy_id))
    ratelist_data = cur.fetchall()
    
    cur.close()
    
    return render_template('medicine_details_page.html', 
                         medicine=medicine, 
                         stock_data=stock_data, 
                         ratelist_data=ratelist_data)