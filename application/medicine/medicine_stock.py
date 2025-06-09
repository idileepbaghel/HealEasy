from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from application.extensions import mysql
from datetime import datetime

medstock = Blueprint('medstock', __name__)

@medstock.route('/medstocks', methods=['GET', 'POST'])
def stock():
    
    if 'user' not in session:
        flash('Please login first', 'error')
        return redirect(url_for('auth_bp.login'))
    
    cur = mysql.connection.cursor()
    pharmacy_id = session['user'].get('pharmacy_service_id')
    
    if request.method=='GET':
        cur.execute(
            """SELECT ps.*, mm.medicine_name
            FROM pharmacy_stock ps
            JOIN pharmacy_medicine mm ON ps.pharmacy_medicine_id = mm.id
            WHERE ps.pharmacy_id=%s
            """, (pharmacy_id,))
        items = cur.fetchall()
        
        # Get all medicine names for dropdown
        cur.execute("SELECT id, medicine_name FROM pharmacy_medicine")
        med_names = cur.fetchall()
        
        return render_template('medicine_stocks.html',
                              items=items,
                              med_names=med_names)
    
    return render_template('medicine_stocks.html', items=items)

@medstock.route('/addmedstock', methods=['POST'])
def addmedstock():
    cur = mysql.connection.cursor()
    
    if request.method=='POST':
        pharmacy_id = request.form['pharmacy_id']
        medicine_id  = request.form['medicine_id']
        quantity = request.form['quantity']
        batch_number = request.form['batch_number']
        expiry_date = request.form['expiry_date']
        purchase_price = request.form['purchase_price']
        selling_price = request.form['selling_price']

        cur.execute("""
            SELECT id FROM pharmacy_stock 
            WHERE pharmacy_id = %s 
            AND pharmacy_medicine_id = %s
        """, (pharmacy_id, medicine_id))
        
        if cur.fetchone():
            flash(f'Cannot add duplicate stock. Medicine already exists.', 'warning')
            return redirect(url_for('medstock.stock'))
        
        cur.execute("""INSERT INTO pharmacy_stock 
                    (pharmacy_id, pharmacy_medicine_id, quantity, batch_number, expiry_date, purchase_price, selling_price) 
                    VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                    (pharmacy_id, medicine_id, quantity, batch_number, expiry_date, purchase_price, selling_price))
                
        mysql.connection.commit()
        flash('Stock added successfully....','success')
        return redirect(url_for('medstock.stock'))
    
@medstock.route('/editmedstock/<int:id>', methods=['POST'])
def editmedstock(id):
        cur = mysql.connection.cursor()
        pharmacy_id = session['user'].get('pharmacy_service_id')
            
        if request.method=='POST':
            pharmacy_id = request.form['pharmacy_id']
            medicine_id  = request.form['medicine_id']
            quantity = request.form['quantity']
            batch_number = request.form['batch_number']
            expiry_date = request.form['expiry_date']
            purchase_price = request.form['purchase_price']
            selling_price = request.form['selling_price']

            cur.execute("""
                SELECT id FROM pharmacy_stock 
                WHERE pharmacy_id = %s 
                AND pharmacy_medicine_id = %s
                AND id != %s
            """, (pharmacy_id, medicine_id, id))
            
            if cur.fetchone():
                flash('Cannot update stock. Another stock entry with same name already exists.', 'warning')
                return redirect(url_for('medstock.stock'))
            
            cur.execute("""UPDATE pharmacy_stock 
                    SET quantity=%s, batch_number=%s, 
                    expiry_date=%s, purchase_price=%s, selling_price=%s 
                    WHERE id=%s AND pharmacy_id=%s""",
                    (quantity, batch_number, expiry_date, 
                        purchase_price, selling_price, id, pharmacy_id))
                    
            mysql.connection.commit()
            flash('Stock updated successfully....','success')
            return redirect(url_for('medstock.stock'))

@medstock.route('/stockdelete/<int:id>', methods=['GET'])
def stockdelete(id):
    cur=mysql.connection.cursor()
    
    cur.execute("DELETE FROM pharmacy_stock WHERE id=%s", (id,))
    mysql.connection.commit()
    
    flash('Stock Deleted Successfully...','success')
    return redirect(url_for('medstock.stock'))