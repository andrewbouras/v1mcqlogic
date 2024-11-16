
from flask import Flask
from routes.generate import generate_bp

app = Flask(__name__)

# Register the blueprint
app.register_blueprint(generate_bp)

# Load configuration
app.config.from_object('config.Config')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)