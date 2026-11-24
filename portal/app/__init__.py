import os

from flask import Flask

from app.extensions import bcrypt, db, login_manager


def create_app():
    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-key-cambiame")
    # SQLAlchemy 2.x prefiere psycopg (v3) por defecto si no se indica driver;
    # forzamos psycopg2 (el que instalamos) de forma explicita.
    database_url = os.environ["DATABASE_URL"]
    if database_url.startswith("postgresql://"):
        database_url = database_url.replace("postgresql://", "postgresql+psycopg2://", 1)
    app.config["SQLALCHEMY_DATABASE_URI"] = database_url
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
        "connect_args": {"options": "-csearch_path=portal"}
    }
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    db.init_app(app)
    bcrypt.init_app(app)
    login_manager.init_app(app)

    from app.models import User

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    from app import routes_admin_usuarios, routes_auth, routes_clientes, routes_dashboard
    from app import routes_finanzas, routes_nomina, routes_solicitudes

    app.register_blueprint(routes_auth.bp)
    app.register_blueprint(routes_dashboard.bp)
    app.register_blueprint(routes_clientes.bp)
    app.register_blueprint(routes_nomina.bp)
    app.register_blueprint(routes_finanzas.bp)
    app.register_blueprint(routes_admin_usuarios.bp)
    app.register_blueprint(routes_solicitudes.bp)

    with app.app_context():
        db.create_all()

    return app
