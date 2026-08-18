
import os
from datetime import timedelta

basedir = os.path.abspath(os.path.dirname(__file__))

class Config:
    # Basic Flask config
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    
    # Database - SQLite for now, easily switch to PostgreSQL later
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        f'sqlite:///{os.path.join(basedir, "marketplace.db")}'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Session configuration
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)
    
    # File uploads (for seller documents later)
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max upload
    UPLOAD_FOLDER = os.path.join(basedir, 'app', 'static', 'uploads')
    
    # Geocoding - Nominatim requires a User-Agent (identify your app)
    GEOCODING_USER_AGENT = 'geo-marketplace-app/1.0'
    GEOCODING_URL = 'https://nominatim.openstreetmap.org/search'
    
    # Pagination
    PRODUCTS_PER_PAGE = 20
    SEARCH_RADIUS_KM = 10  # Default search radius