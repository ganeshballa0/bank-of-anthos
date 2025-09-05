# src/aifrontend/app.py
from flask import Flask, render_template, request, session, redirect
import requests

app = Flask(__name__)
app.secret_key = 'REPLACE_WITH_SECURE_KEY'

@app.route('/', methods=['GET'])
def home():
    return redirect('/login')

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        user = request.form.get('user')
        pw = request.form.get('password')
        # Call the existing user-service login API
        resp = requests.post('http://user-service:80/v1/users:signin', json={
            'email': user, 'password': pw
        })
        if resp.status_code == 200:
            token = resp.json().get('token')
            session['token'] = token
            return redirect('/ai')
        return render_template('login.html', error="Login failed")
    return render_template('login.html')

@app.route('/ai', methods=['GET','POST'])
def ai():
    if 'token' not in session:
        return redirect('/login')
    if request.method == 'POST':
        prompt = request.form.get('prompt')
        # Call the AIruntime service (replace URL as appropriate)
        headers = {'Authorization': f"Bearer {session['token']}"}
        ai_resp = requests.post('http://airuntime:8080/v1/ai', json={'prompt': prompt}, headers=headers)
        answer = ai_resp.json().get('response', '')
        return render_template('ai.html', prompt=prompt, answer=answer)
    return render_template('ai.html')
