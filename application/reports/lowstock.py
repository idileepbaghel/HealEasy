from flask import Blueprint, render_template, session, redirect, url_for, flash
from application.extensions import mysql
from datetime import datetime

med_lowstock = Blueprint('med_lowstock', __name__)

@med_lowstock.route('/low-stock')
def stocks():
    if 'user' not in session:
        flash('Please login first', 'error')
        return redirect(url_for('auth_bp.login'))
    
    try:
        cur = mysql.connection.cursor()
        pharmacy_id = session['user'].get('pharmacy_service_id')
        
        threshold = 10
        
        query = """
        SELECT 
            ps.id, 
            pm.medicine_name, 
            ps.quantity,
            ps.batch_number,
            ps.expiry_date,
            ps.purchase_price, 
            ps.selling_price,
            COALESCE(pr.quantity_per_pack, 1) as quantity_per_pack,
            FLOOR(ps.quantity / COALESCE(pr.quantity_per_pack, 1)) as packets_left
        FROM 
            pharmacy_stock ps
        JOIN 
            pharmacy_medicine pm ON ps.pharmacy_medicine_id = pm.id
        LEFT JOIN 
            pharmacy_ratelist pr ON ps.pharmacy_medicine_id = pr.pharmacy_medicine_id AND pr.pharmacy_id = ps.pharmacy_id
        WHERE 
            ps.pharmacy_id = %s AND 
            FLOOR(ps.quantity / COALESCE(pr.quantity_per_pack, 1)) < %s
        ORDER BY 
            packets_left ASC
        """
        
        cur.execute(query, (pharmacy_id, threshold))
        low_stock_medicines = cur.fetchall()
        
        low_stock_medicines = [med for med in low_stock_medicines if med['packets_left'] < 10]
        
        
        low_stock_medicines.sort(key=lambda x: x['packets_left'])
        
        return render_template(
            'low_stock.html',
            low_stock_medicines=low_stock_medicines,
            low_stock_count=len(low_stock_medicines)
        )
        
    except Exception as e:
        flash(f"Error retrieving low stock data: {str(e)}", "danger")
        return redirect(url_for('auth_bp.dashboard'))
    finally:
        cur.close()

def get_low_stock_count():
    """Function to get low stock count for dashboard"""
    try:
        cur = mysql.connection.cursor()
        pharmacy_id = session['user'].get('pharmacy_service_id')
        threshold = 10  
        
        query = """
        SELECT 
            COUNT(*) as count
        FROM 
            pharmacy_stock ps
        LEFT JOIN 
            pharmacy_ratelist pr ON ps.pharmacy_medicine_id = pr.pharmacy_medicine_id AND pr.pharmacy_id = ps.pharmacy_id
        WHERE 
            ps.pharmacy_id = %s AND 
            FLOOR(ps.quantity / COALESCE(pr.quantity_per_pack, 1)) < %s
        """
        
        cur.execute(query, (pharmacy_id, threshold))
        result = cur.fetchone()
        return result['count'] if result else 0
        
    except Exception as e:
        print(f"Error fetching low stock count: {str(e)}")
        return 0
    finally:
        cur.close()
