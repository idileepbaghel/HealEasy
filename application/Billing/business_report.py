from flask import Blueprint, render_template

# Create a Blueprint for reports
report_bp = Blueprint('report_bp', __name__)

@report_bp.route('/business_report')
def business_report():
    return render_template('business_report.html')