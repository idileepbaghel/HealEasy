from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from application.extensions import mysql

delete_bp = Blueprint('delete_bp', __name__)

@delete_bp.route('/type/delete', methods=['GET'])
def delete():
    id = request.args.get('id')
    type_name=request.args.get('type_name')
    cur = mysql.connection.cursor()

    
    cur.execute("DELETE FROM master_medicine_type WHERE id=%s", (id,))
    mysql.connection.commit()

    flash(f'{type_name} Deleted successfully!', category='success')

    return redirect(url_for('meds.meds'))