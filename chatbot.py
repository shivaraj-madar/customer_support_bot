"""
Customer Support Chatbot — LM Studio + LangChain + LangGraph
"""
import os
import json
from pathlib import Path
from typing import TypedDict, Annotated, List, Optional
from dotenv import load_dotenv

from langchain_openai import ChatOpenAI
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_community.vectorstores import FAISS
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.output_parsers import StrOutputParser
from tickets import create_ticket                 
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages

load_dotenv()

# ── CONFIG ──────────────────────────────────────────────────────
CHAT_MODEL    = os.getenv("CHAT_MODEL", "llama-3.2-1b-instruct")
LM_STUDIO_URL = os.getenv("LM_STUDIO_BASE_URL", "http://localhost:1234/v1")
KB_FILE       = Path(__file__).parent / "knowledge_base.txt"

# ── 1. STATE ────────────────────────────────────────────────────
class SupportState(TypedDict):
    messages:       Annotated[list, add_messages]
    intent:         Optional[str]
    user_id:        Optional[str]
    user_info:      Optional[dict]
    retrieved_docs: Optional[List[str]]
    escalate:       bool
    resolution:     Optional[str]

# ── 2. KNOWLEDGE BASE (RAG) ─────────────────────────────────────
def build_vector_store():
    text     = KB_FILE.read_text(encoding="utf-8")
    splitter = RecursiveCharacterTextSplitter(chunk_size=300, chunk_overlap=50)
    docs     = splitter.create_documents([text])
    embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
    print(f"  ↳ Embedding {len(docs)} chunks with all-MiniLM-L6-v2 (local)...")
    return FAISS.from_documents(docs, embeddings)

def retrieve_docs(query: str, vector_store, k: int = 3) -> List[str]:
    return [doc.page_content for doc in vector_store.similarity_search(query, k=k)]

# ── 3. MOCK BACKEND ─────────────────────────────────────────────
CUSTOMER_DB = {
    "USR001": {"name": "Alice Johnson", "email": "alice@example.com",
               "plan": "Pro", "orders": ["ORD-1234", "ORD-5678"], "open_tickets": 0},
    "USR002": {"name": "Bob Martinez",  "email": "bob@example.com",
               "plan": "Basic", "orders": ["ORD-9999"], "open_tickets": 2},
}

def fetch_user_info(user_id: str) -> dict:
    return CUSTOMER_DB.get(user_id, {"error": "User not found"})

# ── 4. LLM via LM Studio ────────────────────────────────────────
LM_STUDIO_API_KEY = os.getenv("LM_STUDIO_API_KEY", "")

llm = ChatOpenAI(
    base_url=LM_STUDIO_URL,
    api_key=LM_STUDIO_API_KEY,  
    model=CHAT_MODEL,
    temperature=0,
)

# ── 5. GRAPH NODES ──────────────────────────────────────────────
def detect_intent(state: SupportState) -> SupportState:
    prompt = ChatPromptTemplate.from_messages([
        SystemMessage(content=(
            "You are an intent classifier. Respond with ONE word only:\n"
            "refund | shipping | account | technical | billing | escalate | greeting | other\n"
            "No punctuation. No explanation. One word."
        )),
        HumanMessage(content=state["messages"][-1].content),
    ])
    raw   = (prompt | llm | StrOutputParser()).invoke({}).strip().lower().split()[0]
    valid = {"refund","shipping","account","technical","billing","escalate","greeting","other"}
    return {**state, "intent": raw if raw in valid else "other"}

def fetch_user_node(state: SupportState) -> SupportState:
    uid = state.get("user_id")
    return {**state, "user_info": fetch_user_info(uid)} if uid else state

def retrieve_knowledge(state: SupportState, vector_store) -> SupportState:
    docs = retrieve_docs(state["messages"][-1].content, vector_store)
    return {**state, "retrieved_docs": docs}

def generate_response(state: SupportState) -> SupportState:
    context  = "\n\n".join(state.get("retrieved_docs") or [])
    user_ctx = f"\nCustomer: {json.dumps(state.get('user_info'))}" if state.get("user_info") else ""
    system   = (
        "You are a friendly, professional customer support agent.\n"
        "Use only the knowledge base below to answer. Be concise and warm.\n\n"
        f"Knowledge Base:\n{context}{user_ctx}"
    )
    prompt   = ChatPromptTemplate.from_messages([
        SystemMessage(content=system),
        MessagesPlaceholder(variable_name="messages"),
    ])
    response = (prompt | llm | StrOutputParser()).invoke({"messages": state["messages"]})
    return {**state, "messages": state["messages"] + [AIMessage(content=response)]}

def check_escalation(state: SupportState) -> SupportState:
    keywords = ["speak to human","real person","manager","lawsuit","lawyer","sue","transfer me"]
    last     = state["messages"][-1].content.lower()
    escalate = state.get("intent") == "escalate" or any(k in last for k in keywords)
    return {**state, "escalate": escalate}

def escalate_to_human(state: SupportState) -> SupportState:
    """Escalate: save ticket to SQLite, reply with ticket ID."""
    import hashlib
    from datetime import datetime

    # Generate ticket ID
    raw       = str(state["messages"]) + datetime.now().isoformat()
    ticket_id = "TKT-" + hashlib.md5(raw.encode()).hexdigest()[:6].upper()

    user_info = state.get("user_info") or {}
    user_id   = state.get("user_id") or "guest"

    # Detect reason from last user message
    last_msg  = state["messages"][-1].content.lower()
    if any(k in last_msg for k in ["lawsuit", "lawyer", "sue"]):
        reason = "Legal threat"
    elif any(k in last_msg for k in ["manager", "supervisor"]):
        reason = "Requested manager"
    elif any(k in last_msg for k in ["human", "person", "agent"]):
        reason = "Requested human agent"
    else:
        reason = "Escalated by intent classifier"

    # Save to SQLite
    create_ticket(
        ticket_id    = ticket_id,
        user_id      = user_id,
        user_info    = user_info,
        conversation = state["messages"],
        reason       = reason,
    )

    # Reply to user
    msg = (
        f"I'm sorry for the trouble. I've escalated your case to a human agent.\n\n"
        f"Ticket ID: #{ticket_id}\n"
        f"Reason: {reason}\n\n"
        f"An agent will contact you within 2 business hours. "
        f"Is there anything else you'd like me to note for them?"
    )
    return {**state, "messages": state["messages"] + [AIMessage(content=msg)]}

# ── 6. ROUTING ──────────────────────────────────────────────────
def route_after_check(state: SupportState) -> str:
    return "escalate" if state.get("escalate") else "retrieve"

# ── 7. BUILD GRAPH ──────────────────────────────────────────────
def build_graph(vector_store):
    g = StateGraph(SupportState)
    g.add_node("detect_intent",     detect_intent)
    g.add_node("fetch_user",        fetch_user_node)
    g.add_node("check_escalation",  check_escalation)
    g.add_node("retrieve",          lambda s: retrieve_knowledge(s, vector_store))
    g.add_node("generate_response", generate_response)
    g.add_node("escalate",          escalate_to_human)
    g.set_entry_point("detect_intent")
    g.add_edge("detect_intent",     "fetch_user")
    g.add_edge("fetch_user",        "check_escalation")
    g.add_conditional_edges("check_escalation", route_after_check,
        {"escalate": "escalate", "retrieve": "retrieve"})
    g.add_edge("retrieve",          "generate_response")
    g.add_edge("generate_response", END)
    g.add_edge("escalate",          END)
    return g.compile()

# ── 8. BOT CLASS ────────────────────────────────────────────────
class CustomerSupportBot:
    def __init__(self, user_id: Optional[str] = None):
        print(f"\n LM Studio URL   : {LM_STUDIO_URL}")
        print(f" Chat model      : {CHAT_MODEL}")
        print(f" Embedding model : all-MiniLM-L6-v2 (local)")
        print(f" Building knowledge base...")
        self.vector_store         = build_vector_store()
        self.app                  = build_graph(self.vector_store)
        self.user_id              = user_id
        self.conversation_history = []
        print(" Bot ready!\n")

    def chat(self, user_input: str) -> str:
        self.conversation_history.append(HumanMessage(content=user_input))
        state = SupportState(
            messages=self.conversation_history, intent=None,
            user_id=self.user_id, user_info=None,
            retrieved_docs=None, escalate=False, resolution=None,
        )
        result  = self.app.invoke(state)
        ai_msgs = [m for m in result["messages"] if isinstance(m, AIMessage)]
        self.conversation_history = result["messages"]
        return ai_msgs[-1].content if ai_msgs else "Sorry, I could not process that."

# ── 9. CLI ──────────────────────────────────────────────────────
if __name__ == "__main__":
    bot = CustomerSupportBot(user_id="USR001")
    print("=" * 55)
    print("  Local Support Bot  —  type 'quit' to exit")
    print("=" * 55 + "\n")
    while True:
        try:
            user_input = input("You: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nBot: Goodbye! ")
            break
        if not user_input:
            continue
        if user_input.lower() in ("quit", "exit", "bye"):
            print("Bot: Thanks for reaching out. Have a great day!")
            break
        print("Bot:", bot.chat(user_input), "\n")