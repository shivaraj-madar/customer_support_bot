# 🤖 Customer Support Chatbot

![Python](https://img.shields.io/badge/Python-3.10+-blue?style=flat-square&logo=python)
![LangChain](https://img.shields.io/badge/LangChain-0.2-green?style=flat-square)
![LangGraph](https://img.shields.io/badge/LangGraph-0.1-orange?style=flat-square)
![Flask](https://img.shields.io/badge/Flask-3.0-lightgrey?style=flat-square&logo=flask)
![License](https://img.shields.io/badge/License-MIT-purple?style=flat-square)

> A fully local customer support chatbot — no internet, no API cost, no data leaves your machine.

Built with **LM Studio** + **LangChain** + **LangGraph** + **FAISS** + **Flask** + **SQLite**.

---

## ✨ Features

- 🧠 **Intent detection** — understands 8 types of customer queries
- 📚 **RAG search** — answers from real company policy documents, not guesswork
- 💬 **Web chat UI** — proper chat window in the browser (not terminal)
- 🎫 **Ticket system** — escalations saved to SQLite with full conversation transcript
- 👤 **Customer profiles** — personalised replies using user data
- 🔴 **Smart escalation** — detects angry users and keyword triggers automatically
- 💾 **Conversation history** — 4 ways to access and save chat logs
- 🆓 **100% free** — runs on LM Studio locally, zero API cost

---

## 📁 Project Structure

```
customer_support_bot/
├── chatbot.py              # Main bot — LangGraph pipeline + LLM logic
├── app.py                  # Flask server — web chat UI
├── tickets.py              # SQLite database — escalation tickets
├── knowledge_base.txt      # Company policies (edit to customise)
├── templates/
│   ├── index.html          # Chat window
│   ├── admin.html          # Ticket list page
│   └── ticket.html         # Ticket detail + status
├── requirements.txt
├── .env                    # API key + config (git-ignored)
├── .gitignore
└── README.md
```

---

## 🛠️ Tech Stack

| Tool | Package | Purpose |
|------|---------|---------|
| Python 3.10+ | — | Main language |
| LM Studio | `langchain-openai` | Local LLM — Llama 3.2 (free) |
| LangChain | `langchain` | AI pipeline |
| LangGraph | `langgraph` | Conversation flow control |
| FAISS | `faiss-cpu` | Knowledge base search |
| HuggingFace | `sentence-transformers` | Local embeddings |
| Flask | `flask` | Web interface |
| SQLite | built-in | Ticket storage |

---

## ⚙️ Setup

### 1. Clone the repo

```bash
git clone https://github.com/your-username/customer-support-bot.git
cd customer-support-bot
```

### 2. Create virtual environment

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Mac / Linux
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Setup LM Studio

- Download from [lmstudio.ai](https://lmstudio.ai)
- Load the **Llama 3.2 1B Instruct** model
- Go to **Developer → API Keys → Create API Key** and copy it
- Click **Start Server** (runs on `http://localhost:1234`)

### 5. Configure `.env`

```env
LM_STUDIO_BASE_URL=http://localhost:1234/v1
CHAT_MODEL=llama-3.2-1b-instruct
LM_STUDIO_API_KEY=lms-your-key-here
```

### 6. Run

```bash
python app.py
```

Open **http://localhost:5000** in your browser.

---

## 🌐 Pages

| URL | Description |
|-----|-------------|
| `http://localhost:5000` | Chat window |
| `http://localhost:5000/admin` | All tickets (filter by status) |
| `http://localhost:5000/admin/ticket/TKT-xxx` | Ticket detail + transcript |
| `http://localhost:5000/history` | Live conversation history (JSON) |
| `http://localhost:5000/api/stats` | Ticket stats (JSON) |

---

## 🧠 How It Works

```
User message
      │
      ▼
detect_intent ──► fetch_user ──► check_escalation
                                        │
                          ┌─────────────┴─────────────┐
                          │                           │
                       normal                      urgent
                          │                           │
                    retrieve KB               save to SQLite
                          │                           │
                  generate response          Ticket ID + END
                          │
                         END
```

Each step is a **LangGraph node** — state is shared across all nodes so intent detected in step 1 is available when generating the response in step 5.

---

## 💬 Supported Intents

| Intent | Example | Action |
|--------|---------|--------|
| `greeting` | "Hi there!" | Welcome message |
| `refund` | "I want to return my order" | Refund policy from KB |
| `shipping` | "Where is my package?" | Delivery info from KB |
| `account` | "Reset my password" | Account steps from KB |
| `technical` | "App keeps crashing" | Troubleshooting from KB |
| `billing` | "What plans do you offer?" | Pricing from KB |
| `escalate` | "I want to speak to a manager" | Save ticket, human handoff |
| `other` | Anything else | Best-effort answer |

---

## 🔴 Escalation Triggers

Bot automatically escalates when user says any of:

- `"speak to human"` / `"real person"`
- `"manager"` / `"supervisor"`
- `"lawsuit"` / `"lawyer"` / `"sue"`
- `"transfer me"`
- Intent classifier returns `escalate`

Each ticket saves: **ticket ID, customer name, email, plan, reason, full conversation, timestamp, status**.

---

## 💾 Conversation History

Four ways to access chat history:

```python
# 1. Type 'history' in terminal anytime
if user_input.lower() == "history":
    for msg in bot.conversation_history:
        role = "You" if msg.__class__.__name__ == "HumanMessage" else "Bot"
        print(f"  {role}: {msg.content[:80]}")

# 2. Save to JSON file
bot.save_history()
# → history_20250320_143022.json

# 3. Flask route — open in browser
# http://localhost:5000/history

# 4. SQLite permanent storage
save_conversation_history(session_id, user_id, bot.conversation_history)
# → saved to tickets.db, survives restart
```

---

## 📦 requirements.txt

```
langchain>=0.2.0
langchain-core>=0.2.0
langchain-community>=0.2.0
langchain-openai>=0.1.0
langchain-text-splitters>=0.2.0
langgraph>=0.1.0
faiss-cpu>=1.8.0
sentence-transformers>=2.7.0
tiktoken>=0.7.0
python-dotenv>=1.0.0
flask>=3.0.0
```

---

## 🔧 Customisation

### Change the knowledge base
Edit `knowledge_base.txt` with your own company policies. No code change needed — bot re-embeds on every startup.

### Switch LLM model
Update `CHAT_MODEL` in `.env`:

```env
CHAT_MODEL=llama-3.2-1b-instruct    # default — fast (~1GB)
CHAT_MODEL=mistral-7b-instruct      # stronger reasoning (~4GB)
CHAT_MODEL=phi-3-mini               # lightweight (~2GB)
```

### Connect a real customer database
Replace the mock dictionary in `chatbot.py`:

```python
def fetch_user_info(user_id: str) -> dict:
    conn = sqlite3.connect("customers.db")
    row  = conn.execute(
        "SELECT * FROM customers WHERE id = ?", (user_id,)
    ).fetchone()
    return dict(row) if row else {}
```

---

## 🐛 Troubleshooting

| Error | Fix |
|-------|-----|
| `401 AuthenticationError` | Get real API key from LM Studio → Developer → API Keys |
| `ConnectionRefusedError` | Start LM Studio server — click Start Server |
| `Model not found` | Check exact model name in LM Studio, update `.env` |
| `ImportError: text_splitter` | `pip install langchain-text-splitters` |
| `ModuleNotFoundError: dotenv` | `pip install python-dotenv` |
| Slow first run | Normal — `all-MiniLM-L6-v2` (~90MB) downloads once |
| Port 5000 in use | Change in `app.py`: `app.run(port=5001)` |

---

##  Project Completion

| Feature | Status |
|---------|--------|
| Intent detection | ✅ Complete |
| RAG knowledge base | ✅ Complete |
| LangGraph pipeline | ✅ Complete |
| Flask web UI | ✅ Complete |
| SQLite ticket system | ✅ Complete |
| Conversation history | ✅ Complete |
| Real customer database | ⚠️ Mock only |
| Admin login/auth | ⚠️ Not implemented |
| Email notifications | ⚠️ Not implemented |

---

## 🙌 Acknowledgements

- [LangChain](https://github.com/langchain-ai/langchain)
- [LangGraph](https://github.com/langchain-ai/langgraph)
- [LM Studio](https://lmstudio.ai)
- [FAISS](https://github.com/facebookresearch/faiss)
- [Flask](https://flask.palletsprojects.com)

---

## 📄 License

MIT License — free to use, modify, and distribute.
