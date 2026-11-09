"""
Local development server runner for Predictive Maintenance Intelligence.
"""
import os
from app import create_app

app = create_app(os.environ.get("FLASK_ENV", "development"))

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"==================================================")
    print(f" Predictive Maintenance Intelligence System")
    print(f" Local Development Server running on:")
    print(f" http://127.0.0.1:{port}")
    print(f"==================================================")
    app.run(host="127.0.0.1", port=port, debug=True)

