from flask import Blueprint, render_template, request, jsonify, flash, url_for, session, redirect
from application.extensions import mysql
import json
import requests
import os

billing = Blueprint('billing', __name__)

# @billing.route('/generate_bill', methods=['GET'])
# def generate_bill():
#     """Route to display billing form and fetch medicine data"""
#     cur = mysql.connection.cursor()
#     cur.execute("""
#         SELECT 
#             id,
#             ratelist_name,
#             amount,
#             COALESCE(discount, 0) as discount,
#             COALESCE(cgst, 0) as cgst,
#             COALESCE(sgst, 0) as sgst,
#             COALESCE(quantity_per_pack, 1) as quantity_per_pack
#         FROM pharmacy_ratelist
#         ORDER BY ratelist_name ASC
#     """)
#     med_names = cur.fetchall()
#     cur.close()
#     return render_template('billing.html', med_names=med_names)

@billing.route('/debug-form', methods=['POST'])
def debug_form():
    """Simple debug route to catch any form submission"""
    print("=== DEBUG FORM ROUTE HIT ===")
    print(f"All form data: {dict(request.form)}")
    print(f"All form lists: {request.form.to_dict(flat=False)}")
    return jsonify({'received': True, 'data': dict(request.form)})

@billing.route('/test', methods=['GET', 'POST'])
def test_route():
    """Test route to verify blueprint is working"""
    print("=== TEST ROUTE HIT ===")
    return jsonify({'message': 'Billing blueprint is working!', 'method': request.method})

@billing.route('/generate-bill', methods=['GET','POST'])
def generate_bill_post():
    if request.method == "POST":
        """Route to handle bill generation and return data in the required JSON format"""
        print("=== ROUTE HIT: /generate-bill ===")
        print(f"Request method: {request.method}")
        print(f"Content type: {request.content_type}")
        
        # Get all form data using getlist for arrays
        medicine_ids = request.form.getlist('medicine[]')
        quantities = request.form.getlist('quantity[]')
        amounts = request.form.getlist('amount[]')
        discounts = request.form.getlist('discount[]')
        sgst_amounts = request.form.getlist('sgst_amount[]')
        cgst_amounts = request.form.getlist('cgst_amount[]')
        taxable_amounts = request.form.getlist('taxable_amount[]')
        net_amounts = request.form.getlist('net_amount[]')
        
        # Debug prints
        print(f"Medicine IDs: {medicine_ids}")
        print(f"Quantities: {quantities}")
        print(f"Amounts: {amounts}")
        print(f"Net Amounts: {net_amounts}")        # Initialize the response structure
        response_data = {
            "username": str(session.get('username', '48')),  # Get username from session or default to '48'
            "items": [],
            "summary": {
                "totalAmount": "0",
                "subtotalAmount": "0",
                "totalDiscount": "0",
                "specialDiscount": "0",
                "totalGst": "0",
                "netAmount": "0"
            }
        }
        
        # Process medicines and get details from database
        cur = mysql.connection.cursor()
        total_cgst = 0.0
        total_sgst = 0.0
        total_discount = 0.0
        total_net_amount = 0.0
        subtotal_amount = 0.0

        # Process each medicine entry
        for i in range(len(medicine_ids)):
            if medicine_ids[i] and i < len(quantities) and quantities[i]:
                # Get medicine details from database
                cur.execute("""
                    SELECT ratelist_name, amount as unit_price, discount as discount_rate, 
                            cgst as cgst_rate, sgst as sgst_rate
                    FROM pharmacy_ratelist 
                    WHERE id = %s
                """, (medicine_ids[i],))
                
                medicine_details = cur.fetchone()
                
                if medicine_details:
                    quantity = float(quantities[i]) if quantities[i] else 0
                    unit_price = float(medicine_details['unit_price'])
                    discount_rate = float(medicine_details['discount_rate'])
                    cgst_rate = float(medicine_details['cgst_rate'])
                    sgst_rate = float(medicine_details['sgst_rate'])
                    
                    gross_amount = quantity * unit_price
                    discount_amount = gross_amount * (discount_rate / 100)
                    taxable_amount = gross_amount - discount_amount
                    cgst_amount = taxable_amount * (cgst_rate / 100)
                    sgst_amount = taxable_amount * (sgst_rate / 100)
                    net_amount = taxable_amount + cgst_amount + sgst_amount
                    
                    medicine_entry = {
                        "medicine_name": medicine_details['ratelist_name'],
                        "quantity": str(int(quantity)),
                        "amount": str(int(gross_amount)),
                        "discount": str(int(discount_rate)),
                        "cgst_percentage": str(int(cgst_rate)),
                        "cgst_amount": "{:.2f}".format(cgst_amount),
                        "sgst_percentage": str(int(sgst_rate)),
                        "sgst_amount": "{:.2f}".format(sgst_amount),
                        "taxable_amount": str(int(taxable_amount)),
                        "net_amount": "{:.2f}".format(net_amount)
                    }
                    
                    response_data["items"].append(medicine_entry)
                    
                    # Update totals
                    total_cgst += cgst_amount
                    total_sgst += sgst_amount
                    total_discount += discount_amount
                    total_net_amount += net_amount
                    subtotal_amount += gross_amount
        
        total_gst = total_cgst + total_sgst
        total_amount = subtotal_amount - total_discount 
        
        response_data["summary"] = {
            "totalAmount": str(int(total_amount)),
            "subtotalAmount": str(int(subtotal_amount)),
            "totalDiscount": str(int(total_discount)),
            "specialDiscount": "0",
            "igstPercentage": "0",
            "igstAmount": "0",
            "totalGst": "{:.2f}".format(total_gst),
            "netAmount": "{:.2f}".format(total_net_amount)
        }
        
        cur.close()
            
        print("\n=== GENERATED RESPONSE ===")
        print(json.dumps(response_data, indent=2))
        print("=== END OF RESPONSE ===\n")

        url = os.getenv('BILLING_API_URL')
        api_key = os.getenv('BILLING_API_KEY')
        
        if not url or not api_key:
            print("Error: Missing API configuration in environment variables")
            return jsonify({
                'success': False,
                'message': 'API configuration error'
            }), 500
        
        headers = {
            'Content-Type': 'application/json',
            'X-Api-Key': api_key
        }
        
        api_response = requests.post(url, json=response_data, headers=headers)
        if api_response.status_code == 200:
            print(api_response.json()['redirect_url'])
            return redirect(api_response.json()['redirect_url'])
                # print(f"API Response Status: {api_response.status_code}")
                # if api_response.status_code == 200:
                #     print("API Response:", api_response.json())
        else:
            print("API Response Text:", api_response.text)
            return api_response.text

    else:
        """Route to display billing form and fetch medicine data"""
        cur = mysql.connection.cursor()
        cur.execute("""
            SELECT 
                id,
                ratelist_name,
                amount,
                COALESCE(discount, 0) as discount,
                COALESCE(cgst, 0) as cgst,
                COALESCE(sgst, 0) as sgst,
                COALESCE(quantity_per_pack, 1) as quantity_per_pack
            FROM pharmacy_ratelist
            ORDER BY ratelist_name ASC
        """)
        med_names = cur.fetchall()
        cur.close()
        return render_template('billing.html', med_names=med_names)

@billing.route('/api/get_medicine_details/<int:medicine_id>', methods=['GET'])
def get_medicine_details(medicine_id):
    """API endpoint to get medicine price, discount and available quantity"""
    cur = mysql.connection.cursor()
    try:
        cur.execute("""                
                    SELECT 
                id,
                ratelist_name,
                amount,
                COALESCE(discount, 0) as discount,
                COALESCE(cgst, 0) as cgst,
                COALESCE(sgst, 0) as sgst,
                pharmacy_medicine_id
            FROM pharmacy_ratelist
            WHERE id = %s AND is_active = 1
        """, (medicine_id,))
        
        result = cur.fetchone()
        if result and result['pharmacy_medicine_id']:
            cur.execute("""
                SELECT SUM(COALESCE(quantity, 0)) as available_quantity
                FROM pharmacy_stock
                WHERE pharmacy_medicine_id = %s
            """, (result['pharmacy_medicine_id'],))
            
            stock_result = cur.fetchone()
            available_quantity = int(stock_result['available_quantity']) if stock_result and stock_result['available_quantity'] else 0
            
            response_data = {
                'success': True,
                'data': {                    
                    'id': result['id'],
                    'name': result['ratelist_name'],
                    'amount': float(result['amount']),
                    'discount': float(result['discount']),
                    'cgst': float(result['cgst']),
                    'sgst': float(result['sgst']),
                    'available_quantity': available_quantity,
                    'stock_warning': f'Available stock: {available_quantity} units'
                }
            }
            
            # Add warning if stock is low (less than 10 units)
            if available_quantity < 10:
                response_data['data']['stock_warning'] = f'Warning: Low stock! Only {available_quantity} units available.'
            
            return jsonify(response_data)
        return jsonify({
            'success': False,
            'message': 'Medicine not found or not properly linked to inventory'
        }), 404
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error fetching medicine details: {str(e)}'
        }), 500
    finally:
        cur.close()

@billing.route('/api/validate_quantity', methods=['POST'])
def validate_quantity():
    """API endpoint to validate medicine quantity"""
    try:
        data = request.get_json()
        medicine_id = data.get('medicine_id')
        quantity = int(data.get('quantity', 0))
        print(quantity,'qua')

        if not all([medicine_id, quantity]):
            return jsonify({
                'success': False,
                'message': 'Missing required fields'
            }), 400
            
        # Get the pharmacy_medicine_id from pharmacy_ratelist
        cur = mysql.connection.cursor()
        try:
            # First, check if the medicine exists and get its pharmacy_medicine_id
            cur.execute("""
                SELECT pharmacy_medicine_id
                FROM pharmacy_ratelist
                WHERE id = %s
            """, (medicine_id,))
            
            result = cur.fetchone()
            if not result or not result['pharmacy_medicine_id']:
                return jsonify({
                    'success': False,
                    'message': 'Medicine not found or not properly linked to inventory'
                }), 404
                
            pharmacy_medicine_id = result['pharmacy_medicine_id']
            
            # Check available quantity in stock
            cur.execute("""
                SELECT SUM(COALESCE(quantity, 0)) as available_quantity
                FROM pharmacy_stock
                WHERE pharmacy_medicine_id = %s
            """, (pharmacy_medicine_id,))
            
            stock_result = cur.fetchone()
            available_quantity = int(stock_result['available_quantity']) if stock_result and stock_result['available_quantity'] else 0
            print(available_quantity,'ghdgf')
            
            if quantity > available_quantity:
                # Return a warning message with available quantity
                return jsonify({
                    'success': False,
                    'valid': False,
                    'message': f'Warning: Cannot select quantity more than available stock. Only {available_quantity} units available.',
                    'available_quantity': available_quantity
                })
                
            return jsonify({
                'success': True,
                'valid': True,
                'available_quantity': available_quantity,
                'message': f'Available stock: {available_quantity} units'
            })
            
        finally:
            cur.close()

    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error validating quantity: {str(e)}'
        }), 500

@billing.route('/api/calculate_bill', methods=['POST'])
def calculate_bill():
    """API endpoint to calculate final bill with stock validation"""
    try:
        data = request.get_json()
        items = data.get('items', [])
        
        if not items:
            return jsonify({
                'success': False,
                'message': 'No items in bill'
            }), 400

        # Validate stock for all items before processing
        cur = mysql.connection.cursor()
        try:
            stock_warnings = []
            
            for item in items:
                medicine_id = item.get('medicine_id')
                quantity = int(item.get('quantity', 0))
                
                # Get pharmacy_medicine_id
                cur.execute("""
                    SELECT pharmacy_medicine_id
                    FROM pharmacy_ratelist
                    WHERE id = %s
                """, (medicine_id,))
                
                result = cur.fetchone()
                if not result or not result['pharmacy_medicine_id']:
                    stock_warnings.append(f"Medicine ID {medicine_id}: Not found or not linked to inventory")
                    continue
                    
                pharmacy_medicine_id = result['pharmacy_medicine_id']
                
                # Check available quantity
                cur.execute("""
                    SELECT SUM(COALESCE(quantity, 0)) as available_quantity
                    FROM pharmacy_stock
                    WHERE pharmacy_medicine_id = %s
                """, (pharmacy_medicine_id,))
                
                stock_result = cur.fetchone()
                available_quantity = int(stock_result['available_quantity']) if stock_result and stock_result['available_quantity'] else 0
                
                if quantity > available_quantity:
                    stock_warnings.append(f"Medicine ID {medicine_id}: Requested {quantity} units but only {available_quantity} available")
              # If any stock warnings, return them
            if stock_warnings:
                return jsonify({
                    'success': False,
                    'message': 'Stock validation failed',
                    'warnings': stock_warnings
                }), 400
                
        finally:
            cur.close()
        
        # Calculate totals if stock validation passed
        subtotal = sum(float(item['net_amount']) for item in items)
        total_items = sum(int(item['quantity']) for item in items)
        
        # Calculate GST
        total_cgst = sum(float(item.get('cgst_amount', 0)) for item in items)
        total_sgst = sum(float(item.get('sgst_amount', 0)) for item in items)
        
        # If no CGST and SGST, apply IGST at 18%
        total_igst = round(subtotal * 0.18, 2) if total_cgst == 0 and total_sgst == 0 else 0
        
        # Calculate final amount including taxes
        total_amount = subtotal + total_cgst + total_sgst + total_igst
        
        return jsonify({
            'success': True,
            'bill_calculation': {
                'summary': {
                    'total_items': total_items,
                    'sub_total': round(subtotal, 2),
                    'total_cgst': round(total_cgst, 2),
                    'total_sgst': round(total_sgst, 2),
                    'total_igst': round(total_igst, 2),
                    'total_amount': round(total_amount, 2)
                },
                'tax_breakdown': {
                    'cgst_percentage': 9.0 if total_cgst > 0 else 0.0,
                    'sgst_percentage': 9.0 if total_sgst > 0 else 0.0,
                    'igst_percentage': 18.0 if total_igst > 0 else 0.0,
                    'total_tax_amount': round(total_cgst + total_sgst + total_igst, 2)
                },
                'calculation_status': 'completed'
            }
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error calculating bill: {str(e)}'
        }), 500

@billing.route('/api/print_bill_format', methods=['POST'])
def print_bill_format():
    """Route to format and print bill data in the specified JSON format"""
    try:
        data = request.get_json() if request.is_json else request.form.to_dict(flat=False)
          # Format the billing data into the required structure with key-value pairs
        formatted_bill = {
            "org_id": 1,
            "username": data.get('username', [''])[0] if isinstance(data.get('username'), list) else data.get('username', ''),
            "items": {},
            "summary": {
                "totalAmount": "0.00",
                "totalItems": "0"
            }
        }

        # Process medicine items
        medicine_ids = data.get('medicine[]', []) if request.form else data.get('items', [])
        quantities = data.get('quantity[]', [])
        amounts = data.get('amount[]', [])
        discounts = data.get('discount[]', [])
        net_amounts = data.get('net_amount[]', [])

        # Get medicine details and format items as key-value pairs
        cur = mysql.connection.cursor()
        try:
            item_count = 0
            for i in range(len(medicine_ids)):
                if not medicine_ids[i]:
                    continue
                    
                # Get medicine name from database
                cur.execute("""
                    SELECT ratelist_name
                    FROM pharmacy_ratelist 
                    WHERE id = %s
                """, (medicine_ids[i],))
                med_result = cur.fetchone()
                
                if med_result:
                    item_count += 1
                    item_key = f"item_{item_count}"
                    item_data = {
                        "medicine_name": med_result['ratelist_name'],
                        "quantity": str(quantities[i]) if i < len(quantities) else "0",
                        "amount": "{:.2f}".format(float(amounts[i])) if i < len(amounts) and amounts[i] else "0.00",
                        "net_amount": "{:.2f}".format(float(net_amounts[i])) if i < len(net_amounts) and net_amounts[i] else "0.00"
                    }
                    
                    # Add discount if present
                    if i < len(discounts) and discounts[i]:
                        item_data["discount"] = "{:.2f}".format(float(discounts[i]))
                    
                    formatted_bill["items"][item_key] = item_data
            
            # Calculate totals
            total_amount = 0.0
            for item_key, item_data in formatted_bill["items"].items():
                total_amount += float(item_data["net_amount"])
            
            formatted_bill["summary"]["totalAmount"] = "{:.2f}".format(total_amount)
            formatted_bill["summary"]["totalItems"] = str(len(formatted_bill["items"]))
            
            return jsonify(formatted_bill)
            
        finally:
            cur.close()
            
    except Exception as e:
        print(f"Error formatting bill data: {str(e)}")
        return jsonify({
            "success": False,
            "message": f"Error formatting bill data: {str(e)}"
        }), 500