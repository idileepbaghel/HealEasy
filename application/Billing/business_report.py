from flask import Blueprint, redirect, url_for
from itsdangerous import URLSafeSerializer
import os

report_bp = Blueprint('report_bp', __name__)

@report_bp.route('/business_report_proxy')
def business_report_proxy():
    # Base URL
    base_url = os.getenv('BUSINESS_REPORT_API_URL')
    
    # API Key
    api_key = os.getenv('BILLING_API_KEY')

  
    # Secret key for signing (should be in environment variables in production)
    secret_key = os.getenv('SECRET_KEY')
    
    # Create serializer using itsdangerous
    serializer = URLSafeSerializer(secret_key)
    
    # Encode/sign the API key using itsdangerous
    encoded_api_key = serializer.dumps(api_key)
    
    # Construct the final URL with encoded API key as query parameter
    final_url = f"{base_url}?api_key={encoded_api_key}"
    
    # Redirect to the external URL
    return redirect(final_url)

