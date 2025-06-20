from flask import render_template, request, redirect, url_for, flash, session, Blueprint
from application.extensions import mysql

med_bp = Blueprint('meds', __name__)

@med_bp.route('/meds', methods = ['GET', 'POST'])
def meds():
     cur = mysql.connection.cursor()

     if request.method == "GET":
        cur.execute("SELECT * FROM master_medicine_type")
        med = cur.fetchall()
        return render_template('medicine_type.html', data = med)
     

@med_bp.route('/addmeds', methods = ['GET','POST'])
def addmeds():
      
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




@med_bp.route('/edit', methods=['POST'])
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
    

@med_bp.route('/type/delete', methods=['GET'])
def delete():
    id = request.args.get('id')
    type_name=request.args.get('type_name')
    cur = mysql.connection.cursor()

    
    cur.execute("DELETE FROM master_medicine_type WHERE id=%s", (id,))
    mysql.connection.commit()

    flash(f'{type_name} Deleted successfully!', category='success')

    return redirect(url_for('meds.meds'))