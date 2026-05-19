"""
Configuration file for Landsat Classification Web Application
Modify these settings for different deployment scenarios
"""

import os

class Config:
    """Base configuration"""
    
    # Flask Settings
    DEBUG = False
    TESTING = False
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-key-change-in-production'
    
    # Upload Settings
    MAX_CONTENT_LENGTH = 3 * 1024 * 1024 * 1024  # 3 GB max upload (for large Landsat scenes)
    UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'uploads')
    OUTPUT_FOLDER = os.path.join(os.path.dirname(__file__), '..', 'Outputs')
    
    # Allowed file extensions
    ALLOWED_BAND_EXTENSIONS = {'tif', 'TIF'}
    ALLOWED_MTL_EXTENSIONS = {'txt', 'TXT'}
    
    # Processing Settings
    NUM_PROCESSES = 4  # Number of parallel processes
    TIMEOUT_SECONDS = 600  # Processing timeout (10 minutes)
    
    # Model Settings
    MODEL_PATH = os.path.join(OUTPUT_FOLDER, 'best_model.pkl')
    
    # Logging
    LOG_LEVEL = 'INFO'
    LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    # Classification Classes and Colors
    CLASS_NAMES = {
        0: 'Water',
        1: 'Vegetation',
        2: 'Urban',
        3: 'Desert'
    }
    
    CLASS_COLORS = {
        0: '#0055FF',      # Blue
        1: '#228B22',      # Green
        2: '#E60000',      # Red
        3: '#FFD700'       # Yellow
    }
    
    # Band Information
    LANDSAT_BANDS = {
        1: {'name': 'Coastal/Aerosol', 'wavelength': '0.43-0.45 μm'},
        2: {'name': 'Blue', 'wavelength': '0.45-0.51 μm'},
        3: {'name': 'Green', 'wavelength': '0.53-0.59 μm'},
        4: {'name': 'Red', 'wavelength': '0.64-0.67 μm'},
        5: {'name': 'NIR', 'wavelength': '0.85-0.88 μm'},
        6: {'name': 'SWIR1', 'wavelength': '1.57-1.65 μm'},
        7: {'name': 'SWIR2', 'wavelength': '2.11-2.29 μm'},
        8: {'name': 'Panchromatic', 'wavelength': '0.50-0.68 μm'},
        9: {'name': 'Cirrus', 'wavelength': '1.36-1.38 μm'},
        10: {'name': 'Thermal IR', 'wavelength': '10.60-11.19 μm'}
    }
    
    # Pixel size in meters
    PIXEL_SIZE_M = 30
    PIXEL_AREA_M2 = PIXEL_SIZE_M ** 2  # 900 m²

class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    TESTING = False

class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    TESTING = False
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'change-me-in-production'

class TestingConfig(Config):
    """Testing configuration"""
    TESTING = True
    DEBUG = True
    MAX_CONTENT_LENGTH = 100 * 1024 * 1024  # 100 MB for testing

# Select configuration based on environment
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}

def get_config(env=None):
    """Get configuration object"""
    if env is None:
        env = os.environ.get('FLASK_ENV', 'development')
    return config.get(env, config['default'])
