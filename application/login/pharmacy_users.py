from flask import render_template, request, redirect, url_for, flash, session, Blueprint
from application.extensions import mysql
from datetime import datetime
from ..auth.util import hash_pass, verify_pass 

users_bp = Blueprint('users_bp', __name__)

@users_bp.route('/users', methods=['GET', 'POST'])
def users():
    # Check if user is logged in
    if 'user' not in session:
        flash('Please login first', 'error')
        return redirect(url_for('auth_bp.login'))
    
    cur = mysql.connection.cursor()
    
    # Get the pharmacy service ID from the session
    pharmacy_service_id = session['user'].get('pharmacy_service_id')
    
    # If the user is an admin, they can see all users
           
        # Otherwise, only show users from the same pharmacy
    cur.execute("""
        SELECT pharmacy_users.*, pharmacy_service.pharmacy_name 
        FROM pharmacy_users 
        LEFT JOIN pharmacy_service ON pharmacy_users.pharmacy_service_id=pharmacy_service.id
        WHERE pharmacy_users.pharmacy_service_id = %s
    """, (pharmacy_service_id,))
    
    item = cur.fetchall()
    
    # Get pharmacy names for dropdown
    cur.execute("SELECT id, pharmacy_name FROM pharmacy_service")
    pharm_name = cur.fetchall()
    
    return render_template('pharmacy_users.html', item=item, pharm_name=pharm_name)

@users_bp.route('/addusers', methods=['GET', 'POST'])
def addusers():
    cur = mysql.connection.cursor()

    if 'user' not in session:
        flash('Please login first', 'error')
        return redirect(url_for('auth_bp.login'))

    if request.method == "POST":
        full_name = request.form['full_name']
        mobile = request.form['mobile']
        username = request.form['username']
        email = request.form['email']
        pharmacy_service_id = session['pharmacy']['id']
        user_role = request.form['user_role']
        user_type = request.form['user_type']
        password = "healtrail@123"  # Consider hashing in production!

        password = hash_pass(password)

        
        cur.execute("""
            INSERT INTO pharmacy_users 
            (full_name, username, mobile, password, email, pharmacy_service_id, user_role, user_type)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, 
        (full_name, username, mobile, password, email, pharmacy_service_id, user_role, user_type))

        mysql.connection.commit()
        flash('User added successfully', 'success')
        return redirect(url_for('users_bp.users'))


@users_bp.route('/edit_user/<int:id>', methods=['POST'])
def edit_user(id):
    cur = mysql.connection.cursor()
    

    if request.method == "POST":
        # Get form data
        full_name = request.form['full_name']
        mobile = request.form['mobile']
        username = request.form['username']
        email = request.form['email']
        user_role = request.form['user_role']
        user_type = request.form['user_type']
        password = "healtrail@123" 

        password = hash_pass(password)

        updated_by = session.get('user_id', 1)  
        current_time = datetime.now()
        
        cur.execute("""
            UPDATE pharmacy_users 
            SET full_name = %s, username = %s, mobile = %s, 
                password = %s, email = %s, user_role = %s,
                user_type = %s 
            WHERE id = %s
            """, 
            (full_name, username, mobile, password, email, user_role, user_type, id))
        
        mysql.connection.commit()
        
        flash('User updated successfully', 'success')
        return redirect(url_for('users_bp.users'))

@users_bp.route('/delete_user/<int:id>')
def delete_user(id):
    cur = mysql.connection.cursor()
    
    # Delete from database
    cur.execute("DELETE FROM pharmacy_users WHERE id = %s", (id,))
    mysql.connection.commit()
    
    flash('User deleted successfully', 'success')
    return redirect(url_for('users_bp.users'))