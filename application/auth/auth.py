from flask import render_template, request, redirect, url_for, flash, session, abort, Blueprint
from application.extensions import mysql
from .util import hash_pass, verify_pass
from datetime import datetime, timedelta

auth_bp = Blueprint('auth_bp', __name__)

@auth_bp.route('/', methods=['GET', 'POST'])
def dashboard():
    cur = mysql.connection.cursor()
    if request.method == "GET":

        if 'user' not in session:
            flash('Please login first', 'error')
            return redirect(url_for('auth_bp.login'))


        cur.execute("SELECT COUNT(*) AS count FROM pharmacy_medicine")
        result = cur.fetchone()
        
        try:
            if isinstance(result, dict):
                medicine_count = result['count']
            else:
                medicine_count = result[0]
        except (KeyError, IndexError):
            medicine_count = 0


        pharmacy_id = session['user'].get('pharmacy_service_id')        
        cur.execute('''
            SELECT COUNT(*) as count
            FROM pharmacy_stock ps
            JOIN pharmacy_medicine pm ON ps.pharmacy_medicine_id = pm.id
            WHERE ps.pharmacy_id = %s
            AND ps.expiry_date BETWEEN CURDATE() AND DATE_ADD(CURDATE(), INTERVAL 7 DAY)
        ''', (pharmacy_id,))
        expiring_result = cur.fetchone()
        
        try:
            if isinstance(expiring_result, dict):
                expiring_count = expiring_result['count']
            else:
                expiring_count = expiring_result[0]
        except (KeyError, IndexError):
            expiring_count = 0
        
        
        cur.execute('''
            SELECT pm.medicine_name, ps.quantity
            FROM pharmacy_stock ps
            JOIN pharmacy_medicine pm ON ps.pharmacy_medicine_id = pm.id
            WHERE ps.pharmacy_id = %s
            LIMIT 10
        ''', (pharmacy_id,))
        stock_data = cur.fetchall()
        
        medicine_names = []
        quantities = []
        
        if stock_data:
            for row in stock_data:
                if isinstance(row, dict):
                    medicine_names.append(row['medicine_name'])
                    quantities.append(row['quantity'])
                else:
                    medicine_names.append(row[0])
                    quantities.append(row[1])
                cur.close()
        return render_template('dashboard.html', 
                             medicine_count=medicine_count, 
                             expiring_count=expiring_count,
                             batch_numbers=medicine_names,  
                             quantities=quantities)


@auth_bp.route('/api/expiring-medicines', methods=['GET'])
def get_expiring_medicines():
    if 'user' not in session:
        flash('Please login first', 'error')
        return redirect(url_for('auth_bp.login'))
    
    cur = mysql.connection.cursor()
    pharmacy_id = session['user'].get('pharmacy_service_id')
    
    cur.execute('''
        SELECT 
            pm.medicine_name,
            ps.batch_number,
            ps.quantity,
            ps.expiry_date,
            DATEDIFF(ps.expiry_date, CURDATE()) as days_to_expiry
        FROM pharmacy_stock ps
        JOIN pharmacy_medicine pm ON ps.pharmacy_medicine_id = pm.id
        WHERE ps.pharmacy_id = %s
        AND ps.expiry_date BETWEEN CURDATE() AND DATE_ADD(CURDATE(), INTERVAL 7 DAY)
        ORDER BY ps.expiry_date ASC
    ''', (pharmacy_id,))
    
    expiring_medicines = cur.fetchall()
    cur.close()
    
    # Convert to list of dictionaries for JSON response
    medicines_list = []
    for medicine in expiring_medicines:
        if isinstance(medicine, dict):
            medicines_list.append({
                'medicine_name': medicine['medicine_name'],
                'batch_number': medicine.get('batch_number', 'N/A'),
                'quantity': medicine['quantity'],
                'expiry_date': medicine['expiry_date'].strftime('%Y-%m-%d') if medicine['expiry_date'] else 'N/A',
                'days_to_expiry': medicine['days_to_expiry']
            })
        else:
            medicines_list.append({
                'medicine_name': medicine[0],
                'batch_number': medicine[1] if medicine[1] else 'N/A',
                'quantity': medicine[2],
                'expiry_date': medicine[3].strftime('%Y-%m-%d') if medicine[3] else 'N/A',
                'days_to_expiry': medicine[4]
            })
    
    return render_template('dashboard.html', medicines_list)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user_type = request.form.get('user_type')

        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM pharmacy_users WHERE email = %s", (email,))
        user = cur.fetchone()

        if user and verify_pass(password, user['password']):  
            db_user_type = user.get('user_type', '').lower()
            
            if user_type == 'admin' and db_user_type != 'admin':
                flash('You are not authorized to login as admin', 'error')
                return render_template('sign-in.html')
            elif user_type == 'non-admin' and db_user_type == 'admin':
                flash('Admin users must select Admin user type', 'error')
                return render_template('sign-in.html')
            
            session['loggedin'] = True
            session['user'] = user
            session['user_id'] = user['id']
            session['username'] = user['username'] 
            session['selected_user_type'] = user_type
            session['is_admin'] = (user_type == 'admin')  

            cur.execute("SELECT * FROM pharmacy_service WHERE id = %s", (user['pharmacy_service_id'],))
            pharmacy = cur.fetchone()
            session['pharmacy'] = pharmacy

            flash(f"'{ session['pharmacy']['pharmacy_name'] }' successfully logged in as {user_type}", 'success')
            return redirect(url_for('auth_bp.dashboard'))
        else:
            flash('Incorrect email or password, please enter correct details','warning')
    return render_template('sign-in.html')

@auth_bp.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        full_name = request.form['full_name']
        mobile=request.form['mobile']
        username=request.form['username']
        email = request.form['email']
        password = request.form['password']
        user_type = request.form.get('user_type')
        user_role = request.form.get('user_role')
        

        password = hash_pass(password)  

        cur = mysql.connection.cursor()
        cur.execute("INSERT INTO pharmacy_users (full_name,mobile, username, email, password, user_type, user_role) VALUES (%s, %s, %s, %s, %s, %s, %s)", 
                    (full_name, mobile, username, email, password, user_type, user_role))
        mysql.connection.commit()

        return redirect(url_for("auth_bp.login"))
    return render_template('sign-up.html')  


@auth_bp.route('/logout', methods=['GET', 'POST'])
def logout():
    session.clear()
    flash('You are successfully logged out.....','success')
    return redirect(url_for('auth_bp.login'))