# run_with_quiz.py
from mentorIA import app  # importa la app existente (NO modificar app.py)
from quiz import bp as quiz_bp

# Registramos el blueprint con la app importada
app.register_blueprint(quiz_bp)

if __name__ == "__main__":
    # Ejecuta la app combinada
    app.run(host="0.0.0.0", port=int(__import__("os").environ.get("PORT", 5000)), debug=True)
