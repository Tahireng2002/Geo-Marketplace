from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager  # type: ignore
from flask_bcrypt import Bcrypt  # type: ignore[reportMissingImports]
from config import Config
import os

db = SQLAlchemy()
bcrypt = Bcrypt()
login_manager = LoginManager()

login_manager.login_view = 'auth.login'
login_manager.login_message_category = 'info'

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    db.init_app(app)
    bcrypt.init_app(app)
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        from app.models import User
        return User.query.get(int(user_id))

    from app.routes.auth import auth_bp
    from app.routes.main import main_bp
    from app.routes.admin import admin_bp
    from app.routes.products import products_bp
    from app.routes.orders import orders_bp
    from app.routes.returns import returns_bp

    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(main_bp, url_prefix='/')
    app.register_blueprint(admin_bp)
    app.register_blueprint(products_bp)
    app.register_blueprint(orders_bp)
    app.register_blueprint(returns_bp)

    # Make models available in all templates
    @app.context_processor
    def inject_models():
        from app.models import SellerApplication, Product, Order
        return dict(SellerApplication=SellerApplication, Product=Product, Order=Order)

    return app

           