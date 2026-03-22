"""
app.py — Flask web UI for Customer Support Chatbot
Run: python app.py
Open: http://localhost:5000
"""
from tickets import get_all_tickets, get_ticket, update_status, get_stats
from flask import Flask, render_template, request, jsonify, session
from chatbot import CustomerSupportBot
import uuid

app = Flask(__name__)
app.secret_key = "support-bot-secret-key-change-in-prod"

# Store bot instances per session
bots = {}

def get_bot(session_id, user_id=None):
    if session_id not in bots:
        bots[session_id] = CustomerSupportBot(user_id=user_id)
    return bots[session_id]

@app.route("/")
def index():
    if "session_id" not in session:
        session["session_id"] = str(uuid.uuid4())
    return render_template("index.html")

@app.route("/chat", methods=["POST"])
def chat():
    data       = request.get_json()
    user_msg   = data.get("message", "").strip()
    user_id    = data.get("user_id", "USR001")
    session_id = session.get("session_id", str(uuid.uuid4()))

    if not user_msg:
        return jsonify({"error": "Empty message"}), 400

    bot      = get_bot(session_id, user_id=user_id)
    reply    = bot.chat(user_msg)
    intent   = bot.conversation_history[-1].additional_kwargs.get("intent", "") \
               if hasattr(bot.conversation_history[-1], "additional_kwargs") else ""

    return jsonify({"reply": reply, "session_id": session_id})

@app.route("/reset", methods=["POST"])
def reset():
    session_id = session.get("session_id")
    if session_id and session_id in bots:
        del bots[session_id]
    session["session_id"] = str(uuid.uuid4())
    return jsonify({"status": "reset"})

if __name__ == "__main__":
    app.run(debug=True, port=5000)