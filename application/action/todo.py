from flask import Blueprint, render_template, request, jsonify, redirect, url_for, session, flash
from application.extensions import mysql

todo = Blueprint('todo', __name__)

@todo.route('/special_orders')
def index():
    if request.method == 'GET':
        if 'user' not in session:
            flash('Please login first', 'error')
            return redirect(url_for('auth_bp.login'))
        
        cur = mysql.connection.cursor()

        pharmacy_id = session['user'].get('pharmacy_service_id')
        print(pharmacy_id)
        try:
            cur.execute('SELECT * FROM pharmacy_special_order WHERE pharmacy_service_id = %s',(pharmacy_id,))
            tasks = cur.fetchall()
            return render_template('Todo_tasks.html', tasks=tasks)
        finally:
            cur.close()

@todo.route('/todo/add_task', methods=['POST'])
def add_task():
    if 'user' not in session:
        flash('Please login first', 'error')
        return redirect(url_for('auth_bp.login'))
        
    pharmacy_id = session['user'].get('pharmacy_service_id')
    if not pharmacy_id:
        flash('Pharmacy ID not found', 'error')
        return redirect(url_for('auth_bp.login'))

    cur = mysql.connection.cursor()
    try:
        medicine_name = request.form['medicine_name']
        description = request.form['description']
        requester_name = request.form['requester_name']
        requester_contact = request.form['requester_contact']
        quantity = request.form['quantity']
        order_from = request.form['order_from']
        
        cur.execute('''
            INSERT INTO pharmacy_special_order 
            (pharmacy_service_id, medicine_name, description, requester_name, requester_contact, quantity, order_from)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        ''', (pharmacy_id, medicine_name, description, requester_name, requester_contact, quantity, order_from))
        
        mysql.connection.commit()
        flash('Task added successfully', 'success')
        return redirect(url_for('todo.index'))
    except Exception as e:
        flash(f'Error adding task: {str(e)}', 'error')
        return redirect(url_for('todo.index'))
    finally:
        cur.close()

@todo.route('/todo/get_task/<int:task_id>')
def get_task(task_id):
    cur = mysql.connection.cursor()
    try:
        cur.execute('SELECT * FROM pharmacy_special_order WHERE id = %s', (task_id,))
        task = cur.fetchone()
        return jsonify(task)
    finally:
        cur.close()

@todo.route('/todo/edit_task', methods=['POST'])
def edit_task():
    if 'user' not in session:
        flash('Please login first', 'error')
        return redirect(url_for('auth_bp.login'))
        
    pharmacy_id = session['user'].get('pharmacy_service_id')
    if not pharmacy_id:
        flash('Pharmacy ID not found', 'error')
        return redirect(url_for('auth_bp.login'))

    cur = mysql.connection.cursor()
    try:
        task_id = request.form['task_id']
        medicine_name = request.form['medicine_name']
        description = request.form['description']
        requester_name = request.form['requester_name']
        requester_contact = request.form['requester_contact']
        quantity = request.form['quantity']
        order_from = request.form['order_from']
        
        # Verify that the task belongs to this pharmacy
        cur.execute('SELECT pharmacy_service_id FROM pharmacy_special_order WHERE id = %s', (task_id,))
        task = cur.fetchone()
        if not task or task['pharmacy_service_id'] != pharmacy_id:
            flash('Unauthorized access or task not found', 'error')
            return redirect(url_for('todo.index'))
        
        cur.execute('''
            UPDATE pharmacy_special_order 
            SET medicine_name = %s, description = %s, requester_name = %s,
                requester_contact = %s, quantity = %s, order_from = %s
            WHERE id = %s AND pharmacy_service_id = %s
        ''', (medicine_name, description, requester_name, requester_contact, quantity, order_from, task_id, pharmacy_id))
        
        mysql.connection.commit()
        flash('Task updated successfully', 'success')
        return redirect(url_for('todo.index'))
    except Exception as e:
        flash(f'Error updating task: {str(e)}', 'error')
        return redirect(url_for('todo.index'))
    finally:
        cur.close()

@todo.route('/todo/delete_task/<int:task_id>', methods=['DELETE'])
def delete_task(task_id):
    if 'user' not in session:
        return jsonify({'error': 'Not logged in'}), 401
        
    pharmacy_id = session['user'].get('pharmacy_service_id')
    if not pharmacy_id:
        return jsonify({'error': 'Pharmacy ID not found'}), 401

    cur = mysql.connection.cursor()
    try:
        # Verify that the task belongs to this pharmacy
        cur.execute('SELECT pharmacy_service_id FROM pharmacy_special_order WHERE id = %s', (task_id,))
        task = cur.fetchone()
        if not task or task['pharmacy_service_id'] != pharmacy_id:
            return jsonify({'error': 'Unauthorized access or task not found'}), 403
            
        cur.execute('DELETE FROM pharmacy_special_order WHERE id = %s AND pharmacy_service_id = %s', (task_id, pharmacy_id))
        mysql.connection.commit()

        flash('Task Deleted Successfully','success')

        return '', 204
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cur.close()