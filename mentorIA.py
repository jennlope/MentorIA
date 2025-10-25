import os
from flask import Flask, request, jsonify, render_template

app = Flask(__name__)

# -----------------------
# Config
# -----------------------
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

# -----------------------
# Intentar importar SDKs de Gemini (soporta variantes)
# -----------------------
genai = None
genai_client = None
genai_lib = None

try:
    from google import genai as _genai_mod
    genai = _genai_mod
    genai_lib = "google.genai"
except Exception:
    try:
        import google.generativeai as _genai_mod2
        genai = _genai_mod2
        genai_lib = "google.generativeai"
    except Exception:
        genai = None
        genai_lib = None

if GEMINI_API_KEY and genai:
    try:
        if genai_lib == "google.genai":
            genai_client = genai.Client(api_key=GEMINI_API_KEY)
        elif genai_lib == "google.generativeai":
            genai.configure(api_key=GEMINI_API_KEY)
            genai_client = genai
    except Exception as e:
        app.logger.warning("No se pudo inicializar Gemini: %s", e)
        genai_client = None

# -----------------------
# Intentar importar generador local (transformers) como fallback
# -----------------------
generator = None
try:
    from transformers import pipeline
    # modelo pequeño por defecto; cambia si tienes otro
    generator = pipeline("text-generation", model="bigscience/bloom-560m", device=-1)
    app.logger.info("Generador local (transformers) listo.")
except Exception as e:
    app.logger.info("No hay generador local disponible: %s", e)
    generator = None

# -----------------------
# Mensajes culturales y reglas rápidas (saludos/despedidas locales para ahorrar tokens)
# -----------------------
cultural_greetings = {
    "saludo": "Q'hubo pues, mijo 🙌. ¿Qué tema quiere aprender hoy?",
    "despedida": "Listo pues, cuídate — Recordá que aprender es un camino pa’ nunca parar. Seguí curioso, seguí aprendiendo... ¡Pa’lante es pa’ allá, mijo!"
}

def es_saludo_o_despedida(text: str) -> str:
    t = (text or "").lower()
    # simples detecciones; expande si quieres
    if any(k in t for k in ["hola", "buenos", "buenas", "q'hubo", "qhubo", "que hubo", "holá"]):
        return "saludo"
    if any(k in t for k in ["adiós", "adios", "chao", "hasta luego", "nos vemos"]):
        return "despedida"
    return ""

# -----------------------
# PROMPT BASE (no pedir saludos; respuestas cortas y paisas)
# -----------------------
PROMPT_BASE = """
Eres MentorIA, un tutor virtual antioqueño.
RESPONDE EN MÁXIMO 6 LÍNEAS. Usa léxico paisa: mijo, q'hubo, parce, berraquera, arepa, tinto.
Incluye 1 ejemplo local (plaza de mercado, finca cafetera, Feria de las Flores, arepa, buñuelo).
NO incluyas saludo ni despedida — esos se manejan localmente y NO deben aparecer en la respuesta del modelo.
Formato limpio: sin numerales (#) ni asteriscos (*). Frases cortas y saltos de línea.
Termina con una frase motivadora corta.
"""

def limpiar_texto(txt: str) -> str:
    if not isinstance(txt, str):
        txt = str(txt)
    txt = txt.replace("*", "").replace("#", "")
    # normalizar saltos de línea
    txt = txt.replace("\r\n", "\n").replace("\r", "\n")
    # quitar dobles saltos
    while "\n\n" in txt:
        txt = txt.replace("\n\n", "\n")
    return txt.strip()

# -----------------------
# Extraer texto de respuestas Gemini (soporta variantes)
# -----------------------
def extract_text_from_gemini_response(resp, lib):
    try:
        if lib == "google.genai":
            if hasattr(resp, "text") and resp.text:
                return resp.text
            if hasattr(resp, "message") and getattr(resp.message, "parts", None):
                parts = resp.message.parts
                if len(parts) > 0 and getattr(parts[0], "text", None):
                    return parts[0].text
            return str(resp)
        if lib == "google.generativeai":
            if isinstance(resp, dict):
                cands = resp.get("candidates") or resp.get("outputs")
                if cands and len(cands) > 0:
                    first = cands[0]
                    if isinstance(first, dict):
                        for k in ("content", "message", "output", "text"):
                            v = first.get(k)
                            if isinstance(v, str) and v:
                                return v
                            if isinstance(v, dict) and isinstance(v.get("text"), str):
                                return v["text"]
                    elif isinstance(first, str):
                        return first
                if "text" in resp and isinstance(resp["text"], str):
                    return resp["text"]
            return str(resp)
    except Exception:
        return str(resp)
    return str(resp)

# -----------------------
# Generar respuesta (usa saludo local cuando corresponda; prefiere Gemini; fallback a local)
# -----------------------
def generar_respuesta(user_input: str):
    user_input = (user_input or "").strip()
    if not user_input:
        return "Escribí algo, mijo.", "fallback"

    # 1) detectar saludo/despedida y contestar localmente (evita gastar tokens)
    tipo = es_saludo_o_despedida(user_input)
    if tipo:
        return cultural_greetings[tipo], "local"

    # 2) Intentar Gemini si está configurado
    if genai_client:
        try:
            prompt = PROMPT_BASE + f"\n\nPregunta: {user_input}\nRespuesta:"
            if genai_lib == "google.genai":
                chat = genai_client.chats.create(model=GEMINI_MODEL)
                resp = chat.send_message(prompt)
                texto = extract_text_from_gemini_response(resp, genai_lib)
            else:
                # google.generativeai
                try:
                    resp = genai_client.chat.create(model=GEMINI_MODEL, messages=[{"role":"user","content":prompt}])
                except Exception:
                    resp = genai_client.generate(model=GEMINI_MODEL, prompt=prompt)
                texto = extract_text_from_gemini_response(resp, genai_lib)
            texto = limpiar_texto(texto)
            # Si la respuesta sale vacía, forzamos fallback
            if texto:
                return texto, "gemini"
        except Exception as e:
            app.logger.warning("Gemini falló: %s — intentando generador local", e)

    # 3) Fallback: usar generador local si está
    if generator:
        try:
            prompt = PROMPT_BASE + f"\n\nPregunta: {user_input}\nRespuesta:"
            salida = generator(prompt, max_new_tokens=256, do_sample=True, temperature=0.7)
            generated = salida[0].get("generated_text", "")
            # si el prompt aparece en la salida, intentar limpiar
            if prompt in generated:
                generated = generated.split(prompt, 1)[-1]
            generated = limpiar_texto(generated)
            if generated:
                return generated, "local"
        except Exception as e:
            app.logger.error("Generador local falló: %s", e)

    # 4) Fallback final
    return "Ahora mismo no tengo un motor disponible, mijo. Intentá de nuevo más tarde.", "fallback"

# -----------------------
# Rutas Flask
# -----------------------
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/chat", methods=["POST"])
def chat():
    data = request.json or {}
    user_input = data.get("message", "")
    respuesta, fuente = generar_respuesta(user_input)
    app.logger.info("Pregunta: %s — Fuente: %s", (user_input or "")[:120], fuente)
    return jsonify({"response": respuesta, "source": fuente})

# -----------------------
# Run
# -----------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)
