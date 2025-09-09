from flask import Flask, request, session, redirect, url_for, render_template
import requests

app = Flask(__name__)
app.secret_key = "YOUR_SECRET_KEY"  # needed for sessions

# Login page (GET) and handler (POST)
@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        # Call the user-service to authenticate and get JWT
        resp = requests.get("http://userservice:5000/login",
                            params={"username": username, "password": password})
        data = resp.json()
        if 'token' in data:
            session['username'] = username
            session['jwt'] = data['token']  # store JWT for later calls
            return redirect(url_for('chat'))
        else:
            return "Login failed", 401
    # Render login HTML form (not shown)
    return render_template('login.html')

# Chat page (GET) and handler (POST)
@app.route('/ai', methods=['GET','POST'])
def chat():
    if 'jwt' not in session:
        return redirect(url_for('login'))
    if request.method == 'POST':
        prompt = request.form['prompt']
        token = session['jwt']  # retrieve stored JWT
        # Forward the prompt and JWT to the aiservices
        resp = requests.post("http://aiservices:8000/ask",
                             headers={"Authorization": f"Bearer {token}"},
                             json={"prompt": prompt})
        answer = resp.json().get('answer', 'Error')
        return render_template('chat.html', answer=answer, prompt=prompt)
    # Render chat input page (not shown)
    return render_template('chat.html')
