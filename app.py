from flask import Flask, render_template

app = Flask(__name__)

@app.route("/")
def index():
    return render_template("index.html")

if __name__ == "__main__":
    print("AURA SIH26094 Frontend Portal running on http://127.0.0.1:8501")
    print("   Make sure server.py (AI REST API) is running on http://127.0.0.1:5000")
    app.run(port=8501, debug=True)
