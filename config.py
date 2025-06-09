class Config:
    MYSQL_HOST = 'localhost'
    MYSQL_USER = 'root'
    MYSQL_PASSWORD = ''
    MYSQL_PORT = 3306
    MYSQL_DB = 'healeasy_pharmacy'
    MYSQL_CURSORCLASS = 'DictCursor'
    SECRET_KEY = 'sdfsdfsdgsdewt4ww345gert34'
    
    # JWT Configuration
    JWT_SECRET_KEY = 'sdfsdfsdgsdewt4ww345gert34'  # Change this to a secure secret key
    JWT_TOKEN_LOCATION = ['headers']
    JWT_HEADER_NAME = 'Authorization'
    JWT_HEADER_TYPE = 'Bearer'

class DevelopmentConfig(Config):
    DEBUG = True
# class ProductionConfig(Config):
#     DEBUG = False

# class TestingConfig(Config):
#     TESTING = True
#     # Use a separate test database
#     MYSQL_DB = 'healtrail_pharmacy_test'
