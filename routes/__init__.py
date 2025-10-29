from .present_routes import present_bp
from .payment_routes import present_bp as payment_bp

def register_routes(app):
    app.register_blueprint(present_bp)
    app.register_blueprint(payment_bp)