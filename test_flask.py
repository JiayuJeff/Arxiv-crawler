#!/usr/bin/env python3
"""
测试Flask基本功能
"""

from flask import Flask

def test_flask():
    app = Flask(__name__)
    
    @app.route('/')
    def home():
        return '''
        <html>
        <head><title>Test</title></head>
        <body>
            <h1>Flask Test Page</h1>
            <p>If you see this, Flask is working!</p>
        </body>
        </html>
        '''
    
    print("Starting test Flask server on port 8080...")
    try:
        app.run(host='0.0.0.0', port=8080, debug=False)
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_flask()
