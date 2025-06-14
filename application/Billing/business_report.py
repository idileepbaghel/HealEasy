from flask import Blueprint, render_template
import requests
import os

report_bp = Blueprint('report_bp', __name__)

@report_bp.route('/business_report_proxy')
def business_report_proxy():
    import requests
    url = os.getenv('BUSINESS_REPORT_API_URL')
    api_key = os.getenv('BILLING_API_KEY')

    headers = {
        "X-API-Key": api_key
    }

    response = requests.get(url, headers=headers)
    return response.content, response.status_code, response.headers.items()
