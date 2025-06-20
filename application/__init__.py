from flask import Flask
from config import Config
from flask_cors import CORS
import os
from dotenv import load_dotenv
from .extensions import mysql, jwt

from .auth.auth import auth_bp
from .medicine.med_type import med_bp
from .MedNames.med_names import med_name
from .medicine.medicine_unit import med_unit
from .login.pharmacy_users import users_bp
from .medicine.medicine_brand import brand_bp
from .medicine.pharmacy_med import pharm_name
from .medicine.medicine_stock import medstock
from .medicine.med_ratelist import ratelist
from .Billing.billing_route import billing
from .Billing.stock_report import lowstock
from .Billing.business_report import report_bp
from .medicine.pharmacy_details import pharm_details
from .reports.expiry_report import expiry_report
from .action.api import api_bp
from .action.todo import todo

def create_app():
    load_dotenv()
    
    app = Flask(__name__, 
                template_folder='package/templates/',
                static_folder='package/static/', 
                static_url_path='/')    
    app.config.from_object(Config)
    mysql.init_app(app)
    jwt.init_app(app)
    CORS(app, resources={r"/*": {"origins": "*"}})

    blueprints = [
        auth_bp,
        med_unit,
        med_bp,
        med_name,
        pharm_name,
        users_bp,
        brand_bp,
        medstock,
        ratelist,
        billing,
        pharm_details,
        lowstock,
        report_bp,
        api_bp,
        todo,
        expiry_report
    ]
    
    for blueprint in blueprints:
        app.register_blueprint(blueprint)
        
    return app
    