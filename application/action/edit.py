from flask import redirect,request,url_for, flash
from application.extensions import mysql
from flask import Blueprint

edit=Blueprint('edit',__name__)

@edit.route('/update',methods=['GET','POST'])
def update():
    item_id=request.args.get('id')
    cur=mysql.connection.cursor()
    if request.method=='POST':
        print(request.form)
        medicine_name=request.form.get('medname')
        short_name=request.form.get('shortname')
        cur=cur.execute("update master_medicine_unit set unit_name=%s, unit_short_name=%s where id=%s",(medicine_name,short_name,item_id))
        mysql.connection.commit()
        flash('Medicine Unit Updated successfuly....','success')
        return redirect(url_for('data_fetch.fetch'))
    
@edit.route('/delete',methods=['GET'])
def delete():
    item_id=request.args.get('id')
    cur=mysql.connection.cursor()
    cur=cur.execute("DELETE from master_medicine_unit WHERE id=%s",(item_id,))
    mysql.connection.commit()
    flash('Medicine Unit Deleted successfuly....','success')
    return redirect(url_for('data_fetch.fetch'))
        