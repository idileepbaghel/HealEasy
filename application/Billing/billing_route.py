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
        print(f"Net Amounts: {net_amounts}")
        
        # Initialize the response structure
        response_data = {
            "username": str(session.get('username')), 
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
        
        # Stock reduction items
        stock_reduction_items = []

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
                    
                    # Add to stock reduction list
                    stock_reduction_items.append({
                        "medicine_id": medicine_ids[i],
                        "quantity": int(float(quantities[i]))
                    })
                    
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

        # Reduce stock quantities
        if stock_reduction_items:
            try:
                # Call our stock reduction API
                stock_reduction_response = requests.post(
                    url_for('billing.reduce_medicine_stock', _external=True),
                    json={"items": stock_reduction_items},
                    headers={'Content-Type': 'application/json'},
                    cookies=request.cookies  # Forward cookies to maintain session
                )
                
                if not stock_reduction_response.ok:
                    print(f"Stock reduction failed: {stock_reduction_response.text}")
                    # You might want to handle this error, potentially rolling back the bill
                else:
                    print("Stock reduction successful")
            except Exception as e:
                print(f"Error reducing stock: {str(e)}")
        
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
        else:
            print("API Response Text:", api_response.text)
            return api_response.text

    else:
        # Existing GET route code...
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

@billing.route('/api/validate_stock', methods=['POST'])
def validate_stock():
    """
    Validate if there's enough stock for all items before generating a bill
    """
    if 'user' not in session:
        return jsonify({"success": False, "message": "Not authenticated"}), 401
    
    pharmacy_id = session['user'].get('pharmacy_service_id')
    data = request.get_json()
    
    if not data or 'items' not in data:
        return jsonify({"success": False, "message": "Invalid data format"}), 400
    
    items = data['items']
    cur = mysql.connection.cursor()
    
    warnings = []
    
    try:
        for item in items:
            medicine_id = item.get('medicine_id')
            quantity = int(item.get('quantity', 0))
            
            if not medicine_id or not quantity:
                warnings.append(f"Invalid item data: {item}")
                continue
            
            # Get pharmacy_medicine_id from the ratelist
            cur.execute("""
                SELECT pr.pharmacy_medicine_id, pr.ratelist_name
                FROM pharmacy_ratelist pr
                WHERE pr.id = %s
            """, (medicine_id,))
            
            result = cur.fetchone()
            if not result or not result['pharmacy_medicine_id']:
                warnings.append(f"Medicine ID {medicine_id} not found in ratelist or not linked to inventory")
                continue
                
            pharmacy_medicine_id = result['pharmacy_medicine_id']
            medicine_name = result['ratelist_name']
            
            # Get total available quantity
            cur.execute("""
                SELECT SUM(quantity) as total_quantity
                FROM pharmacy_stock 
                WHERE pharmacy_medicine_id = %s AND pharmacy_id = %s AND quantity > 0
            """, (pharmacy_medicine_id, pharmacy_id))
            
            stock_result = cur.fetchone()
            available = int(stock_result['total_quantity']) if stock_result and stock_result['total_quantity'] else 0
            
            if available < quantity:
                warnings.append(f"{medicine_name}: Requested {quantity} units but only {available} available")
        
        if warnings:
            return jsonify({
                "success": False,
                "warnings": warnings
            })
            
        return jsonify({
            "success": True,
            "message": "Stock is available for all items"
        })
    
    except Exception as e:
        return jsonify({"success": False, "message": f"Error: {str(e)}"}), 500
    finally:
        cur.close()

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
    


@billing.route('/reduce-medicine-stock', methods=['POST'])
def reduce_medicine_stock():
    """
    Reduce the stock quantity when medicines are sold in a bill
    """
    if 'user' not in session:
        return jsonify({"success": False, "message": "Not authenticated"}), 401
    
    pharmacy_id = session['user'].get('pharmacy_service_id')
    data = request.get_json()
    
    if not data or 'items' not in data:
        return jsonify({"success": False, "message": "Invalid data format"}), 400
    
    items = data['items']
    cur = mysql.connection.cursor()
    
    success_count = 0
    errors = []
    
    try:
        for item in items:
            medicine_id = item.get('medicine_id')
            quantity = int(item.get('quantity', 0))
            
            if not medicine_id or not quantity:
                errors.append(f"Invalid item data: {item}")
                continue
            
            # Get pharmacy_medicine_id from the ratelist
            cur.execute("""
                SELECT pharmacy_medicine_id
                FROM pharmacy_ratelist
                WHERE id = %s
            """, (medicine_id,))
            
            result = cur.fetchone()
            if not result or not result['pharmacy_medicine_id']:
                errors.append(f"Medicine ID {medicine_id} not found in ratelist or not linked to inventory")
                continue
                
            pharmacy_medicine_id = result['pharmacy_medicine_id']
            
            # Get current stock details to update correctly (FIFO order - oldest stock first)
            cur.execute("""
                SELECT id, quantity, batch_number, expiry_date 
                FROM pharmacy_stock 
                WHERE pharmacy_medicine_id = %s AND pharmacy_id = %s AND quantity > 0
                ORDER BY expiry_date ASC
            """, (pharmacy_medicine_id, pharmacy_id))
            
            stock_records = cur.fetchall()
            
            if not stock_records:
                errors.append(f"No available stock for medicine ID {medicine_id}")
                continue
            
            remaining_quantity = quantity
            
            # Reduce from each batch until quantity is fulfilled
            for record in stock_records:
                if remaining_quantity <= 0:
                    break
                    
                stock_id = record['id']
                available = record['quantity']
                
                # Calculate how much to take from this batch
                to_reduce = min(remaining_quantity, available)
                new_quantity = available - to_reduce
                
                # Update the stock
                cur.execute("""
                    UPDATE pharmacy_stock 
                    SET quantity = %s
                    WHERE id = %s
                """, (new_quantity, stock_id))
                
                remaining_quantity -= to_reduce
            
            if remaining_quantity > 0:
                errors.append(f"Insufficient stock for medicine ID {medicine_id}. Requested: {quantity}, Reduced: {quantity - remaining_quantity}")
            else:
                success_count += 1
        
        # Commit all changes if everything processed
        mysql.connection.commit()
        
        return jsonify({
            "success": True, 
            "message": f"Stock updated successfully for {success_count} medicines",
            "errors": errors if errors else None
        })
    
    except Exception as e:
        mysql.connection.rollback()
        return jsonify({"success": False, "message": f"Error: {str(e)}"}), 500
    finally:
        cur.close()