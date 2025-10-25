"""
Extensión de quizzes para MentorIA.
No modifica mentorIA.py — simplemente lo importa y añade rutas para:
- generar quiz con Gemini (si está disponible)
- generar fallback local si no hay modelo
- manejar /quiz, /grade_quiz y /chat_ext
"""
import json
import uuid
import re
from random import shuffle
from flask import Blueprint, request, jsonify, render_template, url_for
from markupsafe import escape

# --- Importar tu app original (NO se modifica mentorIA.py)
import mentorIA as mentor_mod
from mentorIA import app as main_app, generar_respuesta  # usa la app y función ya existentes

bp = Blueprint("quiz_bp", __name__, template_folder="templates", static_folder="static")

QUIZ_STORE = {}
DEFAULT_NUM_QUESTIONS = 5

# -----------------------
# Utilidades para usar Gemini (si está disponible en mentorIA.py)
# -----------------------
def extract_json_from_text(text: str):
    """Extrae JSON válido dentro de texto."""
    if not text or not isinstance(text, str):
        return None
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None
    candidate = text[start:end+1]
    try:
        return json.loads(candidate)
    except Exception:
        fixed = re.sub(r"//.*?\n", "", candidate)
        fixed = re.sub(r"/\*.*?\*/", "", fixed, flags=re.S)
        fixed = re.sub(r",\s*}", "}", fixed)
        fixed = re.sub(r",\s*]", "]", fixed)
        try:
            return json.loads(fixed)
        except Exception:
            return None

def call_gemini_generate(prompt: str):
    """Intenta usar Gemini del módulo mentorIA (si está configurado)."""
    try:
        genai_client = getattr(mentor_mod, "genai_client", None)
        genai_lib = getattr(mentor_mod, "genai_lib", None)
        GEMINI_MODEL = getattr(mentor_mod, "GEMINI_MODEL", None)
        if not genai_client or not genai_lib:
            return None

        if genai_lib == "google.genai":
            chat = genai_client.chats.create(model=GEMINI_MODEL)
            resp = chat.send_message(prompt)
            extract_fn = getattr(mentor_mod, "extract_text_from_gemini_response", None)
            if extract_fn:
                return extract_fn(resp, genai_lib)
            return getattr(resp, "text", str(resp))
        else:
            try:
                resp = genai_client.chat.create(model=GEMINI_MODEL, messages=[{"role": "user", "content": prompt}])
            except Exception:
                resp = genai_client.generate(model=GEMINI_MODEL, prompt=prompt)
            extract_fn = getattr(mentor_mod, "extract_text_from_gemini_response", None)
            if extract_fn:
                return extract_fn(resp, genai_lib)
            return str(resp)
    except Exception as e:
        main_app.logger.warning("call_gemini_generate fallo: %s", e)
        return None

# -----------------------
# Prompts y fallback local
# -----------------------
def prompt_for_quiz_json(topic: str, n: int = DEFAULT_NUM_QUESTIONS) -> str:
    return f"""Genera un cuestionario de {n} preguntas sobre "{topic}".
Devuélvelo SOLO como JSON válido:

{{
  "topic": "{topic}",
  "questions": [
    {{
      "id": "q1",
      "text": "Texto de la pregunta",
      "options": [{{"key":"a","text":"opción A"}},{{"key":"b","text":"opción B"}},{{"key":"c","text":"opción C"}},{{"key":"d","text":"opción D"}}],
      "answer": "b",
      "explanation": "Explicación breve (1-2 oraciones)"
    }}
  ]
}}"""

def generar_quiz_local(topic: str, n: int = DEFAULT_NUM_QUESTIONS):
    """Crea preguntas variadas con respuestas aleatorias."""
    topic_clean = topic.strip().capitalize() if topic else "El tema"
    questions = []
    for i in range(1, n + 1):
        qid = f"q{i}"
        text = f"Pregunta {i} sobre {topic_clean}: ¿Qué aspecto es importante de {topic_clean}?"
        options = [
            {"key": "a", "text": f"Elemento real de {topic_clean}"},
            {"key": "b", "text": f"Ejemplo incorrecto sobre {topic_clean}"},
            {"key": "c", "text": f"Evento no relacionado"},
            {"key": "d", "text": f"Concepto general sin conexión"},
        ]
        shuffle(options)
        correct_key = options[0]["key"]
        explanation = f"La opción {correct_key} es correcta porque describe algo central de {topic_clean}."
        questions.append({"id": qid, "text": text, "options": options, "answer": correct_key, "explanation": explanation})
    return {"topic": topic_clean, "questions": questions}

# -----------------------
# Generador principal
# -----------------------
def generar_quiz(topic: str, n: int = DEFAULT_NUM_QUESTIONS):
    topic = (topic or "tema general").strip()
    prompt = prompt_for_quiz_json(topic, n)
    model_text = call_gemini_generate(prompt)
    if model_text:
        data = extract_json_from_text(model_text)
        if data and isinstance(data.get("questions"), list):
            for q in data["questions"]:
                opts = q.get("options", [])
                if opts and all(isinstance(o, str) for o in opts):
                    q["options"] = [{"key": chr(97+i), "text": txt} for i, txt in enumerate(opts)]
            return data
    return generar_quiz_local(topic, n)

# -----------------------
# Rutas del blueprint
# -----------------------
@bp.route("/create_quiz", methods=["POST"])
def create_quiz():
    data = request.json or {}
    topic = data.get("topic") or data.get("q") or ""
    n = int(data.get("n") or DEFAULT_NUM_QUESTIONS)
    if not topic:
        return jsonify({"error": "Falta 'topic'"}), 400
    quiz_data = generar_quiz(topic, n)
    quiz_id = str(uuid.uuid4())
    QUIZ_STORE[quiz_id] = quiz_data
    quiz_url = url_for("quiz_bp.take_quiz", quiz_id=quiz_id)
    return jsonify({"quiz_url": quiz_url, "quiz_id": quiz_id})

@bp.route("/quiz/<quiz_id>")
def take_quiz(quiz_id):
    quiz = QUIZ_STORE.get(escape(quiz_id))
    if not quiz:
        return "Quiz no encontrado", 404
    return render_template("quiz_dynamic.html", quiz_id=quiz_id, topic=quiz["topic"], questions=quiz["questions"])

@bp.route("/grade_quiz/<quiz_id>", methods=["POST"])
def grade_quiz_dynamic(quiz_id):
    quiz = QUIZ_STORE.get(escape(quiz_id))
    if not quiz:
        return "Quiz no encontrado", 404
    total = len(quiz["questions"])
    correct = 0
    results = []
    for q in quiz["questions"]:
        qid = q["id"]
        user_ans = (request.form.get(qid) or "").lower().strip()
        correct_key = q["answer"].lower()
        if user_ans == correct_key:
            correct += 1
        results.append({
            "id": qid,
            "text": q["text"],
            "your": user_ans,
            "correct": correct_key,
            "explanation": q["explanation"]
        })
    pct = int(round((correct / total) * 100)) if total > 0 else 0
    return render_template("quiz_result_dynamic.html", quiz_id=quiz_id, correct=correct, total=total, pct=pct, results=results, topic=quiz["topic"])

@bp.route("/chat_ext", methods=["POST"])
def chat_ext():
    data = request.json or {}
    msg = (data.get("message") or "").strip()
    if not msg:
        return jsonify({"response": "Escribí algo, mijo.", "source": "local"})

    lower = msg.lower()

    # Sinónimos y expresiones comunes para pedir un examen o quiz
    triggers = [
        "hazme un examen de",
        "hazme un quiz de",
        "hazme una prueba de",
        "hazme un test de",
        "hazme un parcial de",
        "hazme una evaluación de",
        "quiero un examen de",
        "quiero un quiz de",
        "quiero una prueba de",
        "quiero un test de",
        "quiero un parcial de",
        "quiero una evaluación de",
        "preparame un examen de",
        "preparame un quiz de",
        "preparame una prueba de",
        "preparame un test de",
        "preparame un parcial de",
        "preparame una evaluación de",
        "dame un examen de",
        "dame un quiz de",
        "dame una prueba de",
        "dame un parcial de",
        "dame un test de",
        "hazme un quiz sobre",
        "hazme un examen sobre",
        "hazme una prueba sobre",
        "hazme un test sobre"
    ]

    topic = ""
    for t in triggers:
        if t in lower:
            topic = lower.split(t, 1)[1].strip()
            break


    if topic:
        quiz_data = generar_quiz(topic)
        quiz_id = str(uuid.uuid4())
        QUIZ_STORE[quiz_id] = quiz_data
        quiz_url = url_for("quiz_bp.take_quiz", quiz_id=quiz_id)
        texto = f"Listo pues, mijo. Te preparé un examen de '{topic}'."
        return jsonify({"response": texto, "source": "quiz", "quiz_url": quiz_url})

    # Si no pide examen, delegar a generar_respuesta original
    try:
        res = generar_respuesta(msg)
        if isinstance(res, tuple) and len(res) == 2:
            texto, fuente = res
            return jsonify({"response": texto, "source": fuente})
        return jsonify({"response": str(res), "source": "local"})
    except Exception:
        return jsonify({"response": "Ahora mismo no puedo procesar eso.", "source": "fallback"})
