from flask import Flask
from routes.gastos import gastos_bp

app = Flask(__name__)

# Registrar rutas
app.register_blueprint(gastos_bp)

if __name__ == "__main__":
    app.run()