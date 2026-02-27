import os

class Config:
    DATABASE_URL = os.environ.get(
        'DATABASE_URL',
        'postgresql://ai4se_user:change_me_in_production@postgres:5432/ai4se'
    )
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key')
