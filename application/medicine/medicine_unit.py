from flask import Blueprint,redirect,render_template,request,url_for, flash, session
from application.extensions import mysql


med_unit=Blueprint('edit',__name__)



@med_unit.route('/fetch',methods=['GET','POST'])
def fetch():
    cur= mysql.connection.cursor()
    
    
    cur.execute("SELECT * FROM master_medicine_unit")
    data = cur.fetchall()
    return render_template('medicine_unit.html', data=data)


@med_unit.route('/add',methods=['GET','POST'])
def add():

    if 'user' not in session:
        flash('Please login first', 'error')
        return redirect(url_for('auth_bp.login'))

    cur=mysql.connection.cursor()
    if request.method=='POST':
        unitname=request.form['medname']
        shname=request.form['shortname']

        cur.execute("""
            SELECT * FROM master_medicine_unit 
            WHERE LOWER(unit_name) = LOWER(%s) 
            OR LOWER(unit_short_name) = LOWER(%s)
        """, (unitname, shname))
        existing_unit = cur.fetchone()
        
        if existing_unit:
            flash("Can't add duplicate medicine unit or short name", "danger")
            return redirect(url_for('edit.fetch'))

        cur=cur.execute("INSERT INTO master_medicine_unit (unit_name,unit_short_name) VALUES (%s, %s)", (unitname, shname,))

        flash(f"{unitname} added successfully!",'success')
        
        mysql.connection.commit()
        
        return redirect(url_for('edit.fetch'))

@med_unit.route('/update', methods=['GET', 'POST'])
def update():
    if 'user' not in session:
        flash('Please login first', 'error')
        return redirect(url_for('auth_bp.login'))

    item_id = request.args.get('id')
    cur = mysql.connection.cursor()
    
    if request.method == 'POST':
        medicine_name = request.form.get('medname')
        short_name = request.form.get('shortname')
        
        
        cur.execute("""
            SELECT * FROM master_medicine_unit 
            WHERE (LOWER(unit_name) = LOWER(%s) OR LOWER(unit_short_name) = LOWER(%s))
            AND id != %s
        """, (medicine_name, short_name, item_id))
        existing_unit = cur.fetchone()
        
        if existing_unit:
            flash("Can't add duplicate medicine unit or short name", "danger")
            return redirect(url_for('edit.fetch'))

        cur.execute("""
            UPDATE master_medicine_unit 
            SET unit_name=%s, unit_short_name=%s, updated_by=%s 
            WHERE id=%s
        """, (medicine_name, short_name, session['user']['full_name'], item_id))
        
        mysql.connection.commit()
        flash('Medicine unit updated successfully!', 'success')
        return redirect(url_for('edit.fetch'))
    
@med_unit.route('/delete',methods=['GET'])
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
    return redirect(url_for('edit.fetch'))
        