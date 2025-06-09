from flask import Blueprint, render_template, request, jsonify, flash, url_for
from application.extensions import mysql
import json

billing = Blueprint('billing', __name__)

@billing.route('/generate_bill', methods=['GET'])
def generate_bill():
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

@billing.route('/generate-bill', methods=['POST'])
def generate_bill_post():
    """Route to handle bill generation and capture all form data using getlist"""
    # Add debug prints at the very beginning
    print("=== ROUTE HIT: /generate-bill ===")
    print(f"Request method: {request.method}")
    print(f"Content type: {request.content_type}")
    print(f"Form data keys: {list(request.form.keys())}")
    print(f"Total form fields: {len(request.form)}")
    
    try:
        # Print ALL form data first (for debugging)
        print("\n=== ALL FORM DATA (RAW) ===")
        for key, value in request.form.items():
            print(f"{key}: {value}")
        print("=== END ALL FORM DATA ===\n")
        
        # Get all form data using getlist for arrays
        medicine_ids = request.form.getlist('medicine[]')
        quantities = request.form.getlist('quantity[]')
        amounts = request.form.getlist('amount[]')
        discounts = request.form.getlist('discount[]')
        sgst_amounts = request.form.getlist('sgst_amount[]')
        cgst_amounts = request.form.getlist('cgst_amount[]')
        taxable_amounts = request.form.getlist('taxable_amount[]')
        net_amounts = request.form.getlist('net_amount[]')
        
        # Debug prints for getlist results
        print(f"Medicine IDs: {medicine_ids}")
        print(f"Quantities: {quantities}")
        print(f"Amounts: {amounts}")
        print(f"Discounts: {discounts}")
        
        # Get single value fields if any
        single_fields = {}
        for key in request.form.keys():
            if not key.endswith('[]'):
                single_fields[key] = request.form.get(key)
        
        # Create raw form data structure
        raw_form_data = {
            'medicine_ids': medicine_ids,
            'quantities': quantities,
            'amounts': amounts,
            'discounts': discounts,
            'sgst_amounts': sgst_amounts,
            'cgst_amounts': cgst_amounts,
            'taxable_amounts': taxable_amounts,
            'net_amounts': net_amounts,
            'single_fields': single_fields,
            'total_fields': len(request.form),
            'all_keys': list(request.form.keys())
        }
        
        # Print raw form data in JSON format
        print("\n=== RAW FORM DATA (using getlist) ===")
        print(json.dumps(raw_form_data, indent=2, default=str))
        print("=== END OF RAW FORM DATA ===\n")
        
        # Only process if we have medicine data
        medicines = []
        if medicine_ids:
            for i in range(len(medicine_ids)):
                if medicine_ids[i]:  # Only process rows with selected medicines
                    medicine_data = {
                        'row_index': i,
                        'medicine_id': medicine_ids[i],
                        'quantity': float(quantities[i]) if i < len(quantities) and quantities[i] else 0,
                        'amount': float(amounts[i]) if i < len(amounts) and amounts[i] else 0,
                        'discount': float(discounts[i]) if i < len(discounts) and discounts[i] else 0,
                        'sgst_amount': float(sgst_amounts[i]) if i < len(sgst_amounts) and sgst_amounts[i] else 0,
                        'cgst_amount': float(cgst_amounts[i]) if i < len(cgst_amounts) and cgst_amounts[i] else 0,
                        'taxable_amount': float(taxable_amounts[i]) if i < len(taxable_amounts) and taxable_amounts[i] else 0,
                        'net_amount': float(net_amounts[i]) if i < len(net_amounts) and net_amounts[i] else 0
                    }
                    
                    # Get medicine details from database
                    try:
                        cur = mysql.connection.cursor()
                        cur.execute("""
                            SELECT ratelist_name, amount as unit_price, discount as discount_rate, 
                                   cgst as cgst_rate, sgst as sgst_rate, quantity_per_pack
                            FROM pharmacy_ratelist 
                            WHERE id = %s
                        """, (medicine_ids[i],))
                        medicine_details = cur.fetchone()
                        cur.close()
                        
                        if medicine_details:
                            medicine_data.update({
                                'medicine_name': medicine_details['ratelist_name'],
                                'unit_price': float(medicine_details['unit_price']),
                                'discount_rate': float(medicine_details['discount_rate']),
                                'cgst_rate': float(medicine_details['cgst_rate']),
                                'sgst_rate': float(medicine_details['sgst_rate']),
                                'quantity_per_pack': int(medicine_details['quantity_per_pack'])
                            })
                    except Exception as db_error:
                        print(f"Database error for medicine {medicine_ids[i]}: {str(db_error)}")
                        medicine_data['database_error'] = str(db_error)
                    
                    medicines.append(medicine_data)
        
        # Calculate totals
        totals = {
            'total_cgst': sum(med.get('cgst_amount', 0) for med in medicines),
            'total_sgst': sum(med.get('sgst_amount', 0) for med in medicines),
            'total_igst': 0,
            'sub_total': sum(med.get('taxable_amount', 0) for med in medicines),
            'total_items': sum(med.get('quantity', 0) for med in medicines),
            'total_discount': sum((med.get('amount', 0) * med.get('discount_rate', 0) / 100) if 'discount_rate' in med else 0 for med in medicines),
            'amount_to_be_paid': sum(med.get('net_amount', 0) for med in medicines)
        }
        
        # Complete bill data structure
        complete_bill_data = {
            'raw_form_data': raw_form_data,
            'processed_medicines': medicines,
            'calculated_totals': totals,
            'bill_summary': {
                'total_medicines': len(medicines),
                'total_quantity': totals['total_items'],
                'gross_amount': sum(med.get('amount', 0) for med in medicines),
                'total_discount_amount': totals['total_discount'],
                'taxable_amount': totals['sub_total'],
                'total_cgst': totals['total_cgst'],
                'total_sgst': totals['total_sgst'],
                'total_igst': totals['total_igst'],
                'final_amount': totals['amount_to_be_paid']
            },
            'metadata': {
                'total_rows_submitted': len(medicine_ids) if medicine_ids else 0,
                'valid_medicine_rows': len(medicines),
                'form_fields_count': len(request.form),
                'request_info': {
                    'method': request.method,
                    'content_type': request.content_type,
                    'url': request.url
                }
            }
        }
        
        # Print complete bill data in JSON format
        print("\n=== COMPLETE PROCESSED BILL DATA ===")
        print(json.dumps(complete_bill_data, indent=2, default=str))
        print("=== END OF COMPLETE BILL DATA ===\n")
        
        # Add formatted bill data
        formatted_bill = {
            "org_id": 1,  # You can modify this based on your org ID source
            "username": single_fields.get('username', ''),
            "items": [
                {
                    "medicine_name": med.get('medicine_name', ''),
                    "quantity": str(med.get('quantity', 0)),
                    "amount": "{:.2f}".format(float(med.get('amount', 0))),
                    "net_amount": "{:.2f}".format(float(med.get('net_amount', 0)))
                } for med in medicines
            ],
            "summary": {
                "totalAmount": "{:.2f}".format(float(totals['amount_to_be_paid'])),
                "totalItems": str(totals['total_items'])
            }
        }
        
        # Print formatted bill data
        print("\n=== FORMATTED BILL DATA ===")
        print(json.dumps(formatted_bill, indent=2))
        print("=== END OF FORMATTED BILL DATA ===\n")
        
        # Include formatted data in response
        complete_bill_data['formatted_bill'] = formatted_bill
        
        # Return success response
        return jsonify({
            'success': True,
            'message': 'Bill data captured and processed successfully',
            'data': complete_bill_data,
            'billId': f'BILL_{len(medicines)}_{int(totals["amount_to_be_paid"])}'
        })
        
    except Exception as e:
        error_data = {
            'error': str(e),
            'error_type': type(e).__name__,
            'form_keys': list(request.form.keys()) if request.form else [],
            'form_values': dict(request.form) if request.form else {}
        }
        print("\n=== ERROR DATA ===")
        print(json.dumps(error_data, indent=2, default=str))
        print("=== END OF ERROR DATA ===\n")
        
        return jsonify({
            'success': False,
            'message': f'Error processing bill: {str(e)}',
            'error_data': error_data
        }), 500


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
            # Get the available stock quantity
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
            cur.close()        # Calculate totals if stock validation passed
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
            'data': {
                'total_items': total_items,
                'sub_total': round(subtotal, 2),
                'total_cgst': round(total_cgst, 2),
                'total_sgst': round(total_sgst, 2),
                'total_igst': round(total_igst, 2),
                'total_amount': round(total_amount, 2)
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
        
        # Format the billing data into the required structure
        formatted_bill = {
            "org_id": 1,  # You can modify this based on your org ID source
            "username": data.get('username', [''])[0] if isinstance(data.get('username'), list) else data.get('username', ''),
            "items": [],
            "summary": {
                "totalAmount": "0.00"
            }
        }

        # Process medicine items
        medicine_ids = data.get('medicine[]', []) if request.form else data.get('items', [])
        quantities = data.get('quantity[]', [])
        amounts = data.get('amount[]', [])
        discounts = data.get('discount[]', [])
        net_amounts = data.get('net_amount[]', [])

        # Get medicine details and format items
        cur = mysql.connection.cursor()
        try:
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
                    item = {
                        "medicine_name": med_result['ratelist_name'],
                        "quantity": str(quantities[i]) if i < len(quantities) else "0",
                        "amount": "{:.2f}".format(float(amounts[i])) if i < len(amounts) and amounts[i] else "0.00",
                        "net_amount": "{:.2f}".format(float(net_amounts[i])) if i < len(net_amounts) and net_amounts[i] else "0.00"
                    }
                    
                    # Add discount if present
                    if i < len(discounts) and discounts[i]:
                        item["discount"] = "{:.2f}".format(float(discounts[i]))
                    
                    formatted_bill["items"].append(item)
            
            # Calculate total amount
            total = sum(float(item["net_amount"]) for item in formatted_bill["items"])
            formatted_bill["summary"]["totalAmount"] = "{:.2f}".format(total)
            
            # Add total items count if available
            if formatted_bill["items"]:
                formatted_bill["summary"]["totalItems"] = str(len(formatted_bill["items"]))
            
            # Print formatted bill data
            print("\n=== FORMATTED BILL DATA ===")
            print(json.dumps(formatted_bill, indent=2))
            print("=== END OF FORMATTED BILL DATA ===\n")
            
            return jsonify(formatted_bill)
            
        finally:
            cur.close()
            
    except Exception as e:
        print(f"Error formatting bill data: {str(e)}")
        return jsonify({
            "success": False,
            "message": f"Error formatting bill data: {str(e)}"
        }), 500