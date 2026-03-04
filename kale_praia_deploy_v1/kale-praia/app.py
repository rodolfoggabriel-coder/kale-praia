from flask import Flask, render_template, request
import re

app = Flask(__name__)

def detect_device(user_agent):
    ua = user_agent.lower()
    if re.search(r'(iphone|android.*mobile|windows phone|blackberry|opera mini)', ua):
        return 'mobile'
    elif re.search(r'(ipad|android(?!.*mobile)|tablet)', ua):
        return 'tablet'
    return 'desktop'

@app.route('/')
def index():
    ua = request.headers.get('User-Agent', '')
    device = detect_device(ua)
    return render_template('index.html', device=device)

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=10000)
