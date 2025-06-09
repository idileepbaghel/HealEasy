from flask import render_template, request, redirect, url_for, flash, session, Blueprint
from application.extensions import mysql
from datetime import datetime

brand_bp = Blueprint('brands', __name__)

@brand_bp.route('/brands', methods=['GET', 'POST'])
def brands():
    cur = mysql.connection.cursor()

    if request.method == "GET":
        cur.execute("SELECT * FROM master_medicine_manufacturer")
        manufacturer = cur.fetchall()
        return render_template('medicine_brand.html', data=manufacturer)
    
    elif request.method == "POST":
       
        manufacturer_name = request.form['manufacturer_name']
        description = request.form['description']
        
        
        added_by = session.get('user_id', 1)  
        current_time = datetime.now()
        
       
        cur.execute("""
            INSERT INTO master_medicine_manufacturer 
            (manufacturer_name, description, added_date, added_by) 
            VALUES (%s, %s, %s, %s)
            """, 
            (manufacturer_name, description, current_time, added_by))
        mysql.connection.commit()
        
        flash('Medicine Manufacturer added successfully', 'success')
        return redirect(url_for('brands.brands'))

@brand_bp.route('/edit-brand/<int:id>', methods=['POST'])
def edit_brand(id):
    cur = mysql.connection.cursor()
    
    if request.method == "POST":
        
        manufacturer_name = request.form['manufacturer_name']
        description = request.form['description']
        
       
        updated_by = session.get('user_id', 1)  
        current_time = datetime.now()
        
        # Update database
        cur.execute("""
            UPDATE master_medicine_manufacturer 
            SET manufacturer_name = %s,description = %s, 
                updated_date = %s, updated_by = %s 
            WHERE id = %s
            """, 
            (manufacturer_name, description, current_time, updated_by, id))
        mysql.connection.commit()
        
        flash('Medicine brand updated successfully', 'success')
        return redirect(url_for('brands.brands'))

@brand_bp.route('/delete-brand/<int:id>')
def delete_brand(id):
    cur = mysql.connection.cursor()
    
   
    cur.execute("DELETE FROM master_medicine_manufacturer WHERE id = %s", (id,))
    mysql.connection.commit()
    
    flash('Medicine brand deleted successfully', 'success')
    return redirect(url_for('brands.brands'))