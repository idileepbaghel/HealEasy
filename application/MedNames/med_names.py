from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from application.extensions import mysql

med_name = Blueprint('med_name', __name__)

@med_name.route('/mednames', methods = ['GET','POST'])
def mednames():
    cur = mysql.connection.cursor()

    if request.method == "GET":
        cur.execute("""
            SELECT  master_medicine.*, master_medicine_type.type_name, master_medicine_unit.unit_short_name, master_medicine_manufacturer.manufacturer_name FROM master_medicine 
                    LEFT JOIN master_medicine_type ON master_medicine.type_id=master_medicine_type.id
                    LEFT JOIN master_medicine_unit ON master_medicine.unit_id=master_medicine_unit.id
                    LEFT JOIN master_medicine_manufacturer ON master_medicine.manufacturer_id=master_medicine_manufacturer.id
        """)
        data = cur.fetchall()
        print(data)

        cur.execute("SELECT id, type_name FROM master_medicine_type")
        med_types = cur.fetchall()
        
        cur.execute("SELECT id, unit_short_name FROM master_medicine_unit")
        med_units = cur.fetchall()

        cur.execute("SELECT id, manufacturer_name FROM master_medicine_manufacturer")
        manu=cur.fetchall()
        
        return render_template('meds_name.html', 
                                data=data,
                                med_types=med_types,
                                med_units=med_units,
                                manu=manu)
    return render_template('meds_name.html' )



@med_name.route('/med_details', methods=['POST'])
def med_details():
    cur = mysql.connection.cursor()

    if 'user' not in session:
        flash('Please login first', 'error')
        return redirect(url_for('auth_bp.login'))

    if request.method == 'POST':
        medsname = request.form['medsname']
        genericname = request.form['genericname']
        composition = request.form['composition']
        unit_id = request.form['unit_id']
        type_id = request.form['type_id']
        strenght = request.form['strenght']
        manufacturer_id = request.form['manufacturer_id']
        added_by = session['user']['full_name']

        cur.execute("INSERT INTO master_medicine (medicine_name, generic_name, composition, unit_id, type_id, strength, manufacturer_id, added_by) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
                    (medsname, genericname, composition, unit_id, type_id, strenght, manufacturer_id,added_by))
        
        mysql.connection.commit()
        flash('Medicine Name added successfully!', 'success')
        return redirect(url_for('med_name.mednames'))
    

@med_name.route('/edit_mednames/<int:id>', methods=['POST'])
def edit_mednames(id):
    cur = mysql.connection.cursor()

    if 'user' not in session:
        flash('Please login first', 'error')
        return redirect(url_for('auth_bp.login'))

    # id = request.args.get('id')
    medicine_name=request.args.get('medicine_name')

    if request.method == 'POST':
        medicine_name = request.form['medicine_name']
        genericname = request.form['genericname']
        composition = request.form['composition']
        unit_id = request.form['unit_id']
        type_id = request.form['type_id']
        strenght = request.form['strenght']
        manufacturer_id = request.form['manufacturer_id']
        updated_by = session['user']['full_name']

        cur.execute("UPDATE master_medicine SET medicine_name=%s, generic_name=%s, composition=%s, unit_id=%s, type_id=%s, strength=%s, manufacturer_id=%s, updated_by=%s WHERE id=%s",
                    (medicine_name, genericname, composition, unit_id, type_id, strenght, manufacturer_id, updated_by, id))
        
        mysql.connection.commit()
        flash(f'{medicine_name} updates successfuly......','success')
        return redirect(url_for('med_name.mednames'))
    

@med_name.route('/delete_mednames/<int:id>', methods=['GET','POST'])
def delete_mednames(id):
    cur = mysql.connection.cursor()

    medicine_name=request.args.get('medicine_name')


    cur.execute("DELETE FROM master_medicine WHERE id=%s", (id,))
    mysql.connection.commit()

    flash(f'{medicine_name} Deleted successfuly......','success')
    return redirect(url_for('med_name.mednames'))