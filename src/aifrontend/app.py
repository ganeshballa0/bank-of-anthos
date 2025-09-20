import os
import requests
import jwt
import base64
import json
from flask import Flask, request, redirect, url_for, render_template, make_response
from requests.exceptions import RequestException, HTTPError

def create_app():
    app = Flask(__name__)
    
    # -------------------------------------------------------------------
    # Config (all from environment, no hardcoding)
    # -------------------------------------------------------------------
    app.config["USERSERVICE_URI"] = "http://{}/login".format(
        os.environ["USERSERVICE_API_ADDR"]
    )
    app.config["AIRUNTIME_URI"] = "http://{}/ask".format(
        os.environ["AIRUNTIME_API_ADDR"]
    )
    app.config["PUBLIC_KEY"] = open(os.environ["PUB_KEY_PATH"], "r").read()
    app.config["TOKEN_NAME"] = "token"
    app.config["BACKEND_TIMEOUT"] = int(os.getenv("BACKEND_TIMEOUT", "5"))
    app.config["SCHEME"] = os.environ.get("SCHEME", "http")

    # -------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------
    def verify_token(token):
        """Validate JWT using PUBLIC_KEY"""
        if token is None:
            return False
        try:
            claims = jwt.decode(
                jwt=token,
                key=app.config["PUBLIC_KEY"],
                algorithms=["RS256"],
                options={"verify_signature": True},
            )
            app.logger.info("JWT verified successfully. Claims: %s", claims)
            return True
        except jwt.exceptions.InvalidTokenError as err:
            app.logger.error("Invalid token: %s", str(err))
            return False

    # -------------------------------------------------------------------
    # Routes
    # -------------------------------------------------------------------
    @app.route("/login", methods=["GET", "POST"])
    def login():
        """Authenticate user and set JWT cookie"""
        if request.method == "POST":
            username = request.form["username"]
            password = request.form["password"]

            try:
                resp = requests.get(
                    app.config["USERSERVICE_URI"],
                    params={"username": username, "password": password},
                    timeout=app.config["BACKEND_TIMEOUT"],
                )
                resp.raise_for_status()
                data = resp.json()
            except (RequestException, HTTPError) as e:
                return f"Error contacting userservice: {str(e)}", 500

            if "token" in data:
                token = data["token"]
                response = make_response(redirect(url_for("chat")))
                response.set_cookie(
                    app.config["TOKEN_NAME"],
                    token,
                    httponly=True,
                )
                return response
            else:
                return "Login failed", 401

        return render_template("login.html")

    @app.route("/ai", methods=["GET", "POST"])
    def chat():
        """Chat page — requires JWT cookie"""
        token = request.cookies.get(app.config["TOKEN_NAME"])
        if not verify_token(token):
            return redirect(url_for("login"))

        # Decode JWT to get the actual username
        username = "unknown-user"
        try:
            payload_part = token.split(".")[1]
            payload_part += "=" * ((4 - len(payload_part) % 4) % 4)  # pad base64
            payload_bytes = base64.urlsafe_b64decode(payload_part)
            payload = json.loads(payload_bytes)
            username = payload.get("user") or payload.get("sub") or payload.get("username") or "unknown-user"
            app.logger.info("Extracted username from JWT: %s", username)
        except Exception as e:
            app.logger.error("Error decoding JWT payload: %s", str(e))

        answer = None
        prompt = None
        if request.method == "POST":
            user_prompt = request.form["prompt"]
            # Include username and token in the prompt for AI runtime
            prompt = f"My user details:\nUsername: {username}\nToken: {token}\n{user_prompt}"
            app.logger.info("Sending prompt to AI Runtime for user: %s", username)

            try:
                resp = requests.post(
                    app.config["AIRUNTIME_URI"],
                    headers={"Authorization": f"Bearer {token}"},
                    json={"prompt": prompt},
                    timeout=app.config["BACKEND_TIMEOUT"],
                )
                resp.raise_for_status()
                answer = resp.json().get("answer", "Error")
                app.logger.info("Received answer from AI Runtime: %s", answer)
            except (RequestException, HTTPError) as e:
                app.logger.error("Error contacting AI Runtime: %s", str(e))
                return f"Error contacting AI Runtime: {str(e)}", 500

            # Keep original user input in UI
            prompt = user_prompt

        return render_template(
            "chat.html",
            answer=answer,
            prompt=prompt,
            token=token,
            username=username
        )

    @app.route("/logout", methods=["POST"])
    def logout():
        """Clear JWT cookie"""
        response = make_response(redirect(url_for("login")))
        response.delete_cookie(app.config["TOKEN_NAME"])
        return response

    @app.route("/healthz")
    def healthz():
        return "ok", 200

    return app

# -------------------------------------------------------------------
if __name__ == "__main__":
    aifrontend = create_app()
    aifrontend.run(host="0.0.0.0", port=8080)
