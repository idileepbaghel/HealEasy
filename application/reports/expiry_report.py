from flask import Blueprint, render_template, send_file, session, redirect, url_for, flash
from application.extensions import mysql
from datetime import datetime, timedelta
import io
import xlsxwriter

expiry_report = Blueprint('expiry_report', __name__)

@expiry_report.route('/expiry_report')
def index():
    if 'user' not in session:
        flash('Please login first', 'error')
        return redirect(url_for('auth_bp.login'))
        
    pharmacy_id = session['user'].get('pharmacy_service_id')
    if not pharmacy_id:
        flash('Pharmacy ID not found', 'error')
        return redirect(url_for('auth_bp.login'))

    cur = mysql.connection.cursor()
    try:
        # Get medicines expiring within 7 days
        cur.execute('''
            SELECT 
                pm.medicine_name,
                ps.batch_number,
                ps.quantity,
                ps.expiry_date,
                DATEDIFF(ps.expiry_date, CURDATE()) as days_until_expiry
            FROM pharmacy_stock ps
            JOIN pharmacy_medicine pm ON ps.pharmacy_medicine_id = pm.id
            WHERE ps.pharmacy_id = %s
            AND ps.expiry_date BETWEEN CURDATE() AND DATE_ADD(CURDATE(), INTERVAL 7 DAY)
            ORDER BY ps.expiry_date ASC
        ''', (pharmacy_id,))
        
        medicines = cur.fetchall()
        return render_template('expiry_report.html', medicines=medicines)
    except Exception as e:
        flash(f'Error fetching data: {str(e)}', 'error')
        return redirect(url_for('auth_bp.login'))
    finally:
        cur.close()

@expiry_report.route('/download-expiry-report')
def download_report():
    if 'user' not in session:
        flash('Please login first', 'error')
        return redirect(url_for('auth_bp.login'))
        
    pharmacy_id = session['user'].get('pharmacy_service_id')
    if not pharmacy_id:
        flash('Pharmacy ID not found', 'error')
        return redirect(url_for('auth_bp.login'))

    cur = mysql.connection.cursor()
    try:
        # Get medicines expiring within 7 days
        cur.execute('''
            SELECT 
                pm.medicine_name,
                ps.batch_number,
                ps.quantity,
                ps.expiry_date,
                DATEDIFF(ps.expiry_date, CURDATE()) as days_until_expiry
            FROM pharmacy_stock ps
            JOIN pharmacy_medicine pm ON ps.pharmacy_medicine_id = pm.id
            WHERE ps.pharmacy_id = %s
            AND ps.expiry_date BETWEEN CURDATE() AND DATE_ADD(CURDATE(), INTERVAL 7 DAY)
            ORDER BY ps.expiry_date ASC
        ''', (pharmacy_id,))
        
        medicines = cur.fetchall()

        # Create an Excel file in memory
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output)
        worksheet = workbook.add_worksheet()

        # Add headers
        headers = ['Medicine Name', 'Batch Number', 'Quantity', 'Expiry Date', 'Days Until Expiry']
        for col, header in enumerate(headers):
            worksheet.write(0, col, header)

        # Add data
        for row, medicine in enumerate(medicines, 1):
            worksheet.write(row, 0, medicine['medicine_name'])
            worksheet.write(row, 1, medicine['batch_number'])
            worksheet.write(row, 2, medicine['quantity'])
            worksheet.write(row, 3, medicine['expiry_date'].strftime('%Y-%m-%d'))
            worksheet.write(row, 4, medicine['days_until_expiry'])

        workbook.close()
        output.seek(0)

        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=f'expiring_medicines_report_{datetime.now().strftime("%Y%m%d")}.xlsx'
        )
    except Exception as e:
        flash(f'Error generating report: {str(e)}', 'error')
        return redirect(url_for('expiry_report.index'))
    finally:
        cur.close()