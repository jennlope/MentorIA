from flask import Flask, request, jsonify, render_template
from transformers import pipeline

app = Flask(__name__)

# Pipeline de generación de texto con Falcon-7B-Instruct
# device=-1 para CPU, device=0 si tienes GPU
generator = pipeline(
    'text-generation',
    model='bigscience/bloom-560m',
    device=-1  # CPU
)


# Mensajes culturales básicos
cultural_responses = {
    "saludo": "¡Hola parce! Soy MentorIA, tu tutor virtual antioqueño. ¿Qué tema quieres aprender hoy?",
    "despedida": "¡Listo pues, cuídate y sigue estudiando con ganas!"
}

def generar_respuesta(user_input, nivel="basico"):
    user_input_lower = user_input.lower()

    # Saludos y despedidas
    if "hola" in user_input_lower:
        return cultural_responses['saludo']
    if "adiós" in user_input_lower or "chao" in user_input_lower:
        return cultural_responses['despedida']

    # Prompt dinámico para Falcon
    prompt = f"""
Eres MentorIA, un tutor virtual antioqueño. Responde pedagógicamente adaptando la explicación al nivel del estudiante: {nivel}.
Explica el tema de manera clara, con ejemplos locales y cercanos, y mantén un tono amigable y motivador.

Pregunta del estudiante: {user_input}
Respuesta:
"""

    # Generar texto
    salida = generator(prompt, max_length=200, do_sample=True, temperature=0.7)
    return salida[0]['generated_text']

# Rutas Flask
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/chat", methods=["POST"])
def chat():
    data = request.json
    user_input = data.get("message")
    nivel = data.get("nivel", "basico")
    respuesta = generar_respuesta(user_input, nivel)
    return jsonify({"response": respuesta})

if __name__ == "__main__":
    app.run(debug=True)
