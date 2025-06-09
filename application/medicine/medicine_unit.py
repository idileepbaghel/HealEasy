from flask import Blueprint,redirect,render_template,request,url_for, flash, session
from application.extensions import mysql


edit=Blueprint('edit',__name__)

@edit.route('/update', methods=['GET', 'POST'])
def update():
    if 'user' not in session:
        flash('Please login first', 'error')
        return redirect(url_for('auth_bp.login'))

    item_id = request.args.get('id')
    cur = mysql.connection.cursor()
    
    if request.method == 'POST':
        medicine_name = request.form.get('medname')
        short_name = request.form.get('shortname')
        
        # Check if unit name already exists (excluding current unit)
        cur.execute("""
            SELECT * FROM master_medicine_unit 
            WHERE (LOWER(unit_name) = LOWER(%s) OR LOWER(unit_short_name) = LOWER(%s))
            AND id != %s
        """, (medicine_name, short_name, item_id))
        existing_unit = cur.fetchone()
        
        if existing_unit:
            flash("Can't add duplicate medicine unit or short name", "danger")
            return redirect(url_for('data_fetch.fetch'))

        cur.execute("""
            UPDATE master_medicine_unit 
            SET unit_name=%s, unit_short_name=%s, updated_by=%s 
            WHERE id=%s
        """, (medicine_name, short_name, session['user']['full_name'], item_id))
        
        mysql.connection.commit()
        flash('Medicine unit updated successfully!', 'success')
        return redirect(url_for('data_fetch.fetch'))
    
@edit.route('/delete',methods=['GET'])
def delete():

    if 'user' not in session:
        flash('Please login first', 'error')
        return redirect(url_for('auth_bp.login'))

    item_id=request.args.get('id')
    cur=mysql.connection.cursor()

    cur.execute("SELECT unit_name FROM master_medicine_unit WHERE id=%s", (item_id,))
    unit = cur.fetchone()

    cur=cur.execute("DELETE from master_medicine_unit WHERE id=%s",(item_id,))
    mysql.connection.commit()
    return redirect(url_for('data_fetch.fetch'))
        