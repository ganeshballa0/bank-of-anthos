import os, requests, jwt
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
    app.config["AISERVICES_URI"] = "http://{}/ask".format(
        os.environ["AISERVICES_API_ADDR"]
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
            jwt.decode(
                jwt=token,
                key=app.config["PUBLIC_KEY"],
                algorithms=["RS256"],
                options={"verify_signature": True},
            )
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

        if request.method == "POST":
            prompt = request.form["prompt"]
            try:
                resp = requests.post(
                    app.config["AISERVICES_URI"],
                    headers={"Authorization": f"Bearer {token}"},
                    json={"prompt": prompt},
                    timeout=app.config["BACKEND_TIMEOUT"],
                )
                resp.raise_for_status()
                answer = resp.json().get("answer", "Error")
            except (RequestException, HTTPError) as e:
                return f"Error contacting AIServices: {str(e)}", 500

            return render_template("chat.html", answer=answer, prompt=prompt)

        return render_template("chat.html")

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