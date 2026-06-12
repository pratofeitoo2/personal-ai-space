"""Chat API — natural language queries via Ollama LLM."""
import json
import urllib.request
from flask import Blueprint, jsonify, request
from web.config import OLLAMA_BASE, DAEMON_BASE

chat_bp = Blueprint("chat", __name__)

# Intent catalogue — maps user phrases to engine commands
INTENTS = [
    {"phrase": "tasks", "keywords": ["task", "todo", "to-do", "plate", "do today"], "agent": "task-coordinator", "command": "get_today"},
    {"phrase": "habits", "keywords": ["habit", "streak", "routine"], "agent": "insight-generator", "command": "analyse_habits"},
    {"phrase": "calendar", "keywords": ["calendar", "event", "meeting", "schedule"], "agent": "reminder-system", "command": "get_events"},
    {"phrase": "jobs", "keywords": ["job", "application", "apply", "career"], "agent": "task-coordinator", "command": "get_all_open"},
    {"phrase": "goals", "keywords": ["goal", "objective", "target"], "agent": "insight-generator", "command": "get_goals"},
    {"phrase": "digest", "keywords": ["digest", "summary", "overview", "what's on"], "agent": None, "command": "daily_digest"},
]


def classify_intent(text):
    """Simple keyword-based intent classification."""
    text_lower = text.lower()
    for intent in INTENTS:
        for kw in intent["keywords"]:
            if kw in text_lower:
                return intent
    return None


def query_ollama(prompt, model="llama3.2:3b"):
    """Query Ollama for text generation."""
    payload = json.dumps({
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {"num_ctx": 8192}
    }).encode()
    req = urllib.request.Request(
        f"{OLLAMA_BASE}/api/generate",
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    resp = urllib.request.urlopen(req, timeout=120)
    return json.loads(resp.read())["response"]


@chat_bp.route("/", methods=["POST"])
def chat():
    """Process a natural language query.

    POST body: {"message": "what's on my plate today?"}
    """
    data = request.get_json()
    message = data.get("message", "").strip()
    if not message:
        return jsonify({"error": "Empty message"}), 400

    # Step 1: Try keyword classification
    intent = classify_intent(message)

    if intent:
        # Step 2: Execute the engine command
        try:
            if intent["command"] == "daily_digest":
                resp = urllib.request.Request(
                    f"{DAEMON_BASE}/engine",
                    data=json.dumps({"method": "daily_digest", "args": [], "kwargs": {}}).encode(),
                    headers={"Content-Type": "application/json"},
                )
                result = urllib.request.urlopen(resp, timeout=15)
                raw = result.json()
            else:
                resp = urllib.request.Request(
                    f"{DAEMON_BASE}/execute",
                    data=json.dumps({
                        "agent": intent["agent"],
                        "command": intent["command"],
                        "data": {},
                    }).encode(),
                    headers={"Content-Type": "application/json"},
                )
                result = urllib.request.urlopen(resp, timeout=15)
                raw = result.json()

            # Step 3: Format response
            return jsonify({
                "intent": intent["phrase"],
                "data": raw,
                "message": f"Here's what I found about {intent['phrase']}:"
            })
        except Exception as e:
            return jsonify({"error": f"Engine error: {str(e)}"}), 503

    # Step 4: Fallback to Ollama for free-form questions
    try:
        # Gather context
        context_parts = []
        try:
            resp = urllib.request.urlopen(f"{DAEMON_BASE}/engine", timeout=5,
                data=json.dumps({"method": "daily_digest", "args": [], "kwargs": {}}).encode(),
                headers={"Content-Type": "application/json"})
            context_parts.append("Daily digest: " + resp.read().decode()[:500])
        except Exception:
            pass

        context_str = "\n".join(context_parts) if context_parts else "No context available."
        full_prompt = f"""You are a personal AI assistant. Answer the user's question based on the context below.
Be concise and helpful. If you don't have enough information, say so.

Context:
{context_str}

User: {message}
:"""

        response = query_ollama(full_prompt)
        return jsonify({
            "intent": "llm",
            "message": response,
        })
    except Exception as e:
        return jsonify({
            "intent": "error",
            "message": f"I couldn't process that request. Error: {str(e)}",
        }), 503
