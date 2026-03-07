from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class LlmConfig(db.Model):
    __tablename__ = 'llm_config'

    id = db.Column(db.Integer, primary_key=True)
    config_key = db.Column(db.String(64), unique=True, nullable=False)
    api_key = db.Column(db.Text, nullable=False)
    base_url = db.Column(db.Text, nullable=False)
    model = db.Column(db.String(128), nullable=False)
    description = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    updated_at = db.Column(db.DateTime, server_default=db.func.now(), onupdate=db.func.now())

    def to_dict(self):
        return {
            'id': self.id,
            'config_key': self.config_key,
            'base_url': self.base_url,
            'model': self.model,
            'description': self.description
            # Note: api_key is intentionally not returned for security
        }