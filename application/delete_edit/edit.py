from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from application.extensions import mysql

edit_bp = Blueprint('edit_bp', __name__)

@edit_bp.route('/edit', methods=['POST'])
def edit():

    if 'user' not in session:
        flash('Please login first', 'error')
        return redirect(url_for('auth_bp.login'))

    id = request.args.get('id')
    type_name=request.args.get('type_name')
    cur = mysql.connection.cursor()
    if request.method == 'POST':
        type = request.form['type']
        description = request.form['description']
        updated_by = session['user']['full_name']

        cur.execute("""
            SELECT * FROM master_medicine_type 
            WHERE LOWER(type_name) = LOWER(%s) AND id != %s
        """, (type, id))
        existing_medicine = cur.fetchone()
        
        if existing_medicine:
            flash("Can't add duplicate medicine's type", "danger")
            return redirect(url_for('meds.meds'))

        cur.execute("""
            UPDATE master_medicine_type
            SET type_name=%s, description=%s, updated_by=%s
            WHERE id= %s """, (type, description, updated_by, id))

        mysql.connection.commit()
        flash(f'{type_name} updated successfully!', category='success')
        return redirect(url_for('meds.meds'))
    
