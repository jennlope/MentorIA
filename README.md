# MentorIA - Tu Tutor Virtual Antioqueño

Aplicación web de chat educativo culturalmente antioqueño, construida con **Flask** en el backend y HTML/CSS/JS puro en el frontend.  
MentorIA usa **Gemini** (cuando la API está disponible) y si falla, recurre a un **modelo local con Transformers** como respaldo.  

---

## Inicio Rápido

### Prerrequisitos
- Python 3.9 o superior  
- Virtualenv recomendado  
- API Key de **Gemini** (Google Generative AI)  

### Instalación

1. Clona este repositorio:

```bash
git clone https://github.com/tuusuario/mentoria.git
cd mentoria
```

2. Crea y activa un entorno virtual:

```bash
python -m venv venv
# Windows (PowerShell)
.\venv\Scripts\Activate
# Linux / MacOS
source venv/bin/activate
```

3. Instala dependencias:
```bash
pip install -r requirements.txt
```


4. Configura tu API Key de Gemini:
```bash
# Windows (PowerShell)
$Env:GEMINI_API_KEY="tu_api_key_aqui"

# Linux / MacOS
export GEMINI_API_KEY="tu_api_key_aqui"
```

### ▶️ Ejecución

Inicia el servidor Flask:
```bash
python MentorIA.py
```

Luego abre en tu navegador:
```bash 
http://localhost:5000
```

## Flujo de la Aplicación

### Pantalla de Carga
Fondo verde con el logo de MentorIA.

### Pantalla de Bienvenida
Texto introductorio, imagen de robot, checkbox de consentimiento y botón Comenzar.
El botón solo se habilita al aceptar el uso de datos.

### Pantalla de Chat

- Barra superior con foto de perfil y estado de MentorIA.

- Chat responsivo con burbujas (verde para usuario, gris para el bot).

- Botón verde de envío.

- Avatar del bot junto a cada mensaje.

## Integración con IA

- Principal: Google Gemini (via google-generativeai).

- Fallback: Modelo local con transformers (BigScience/Bloom).

- El sistema adapta las respuestas a un estilo paisa, usando expresiones locales como mijo, parce, arepas, berraquera.

- El prompt base asegura explicaciones claras, cortas y culturales.

## Diseño Responsive

- Compatible con móvil, tablet y escritorio.

- Imágenes y burbujas se adaptan automáticamente al ancho de pantalla.

- Input y botón de enviar se ajustan en pantallas pequeñas.

## Stack Tecnológico

- **Backend:** Flask (Python)

- **Frontend:** HTML5 + CSS3 + JS

- **IA:** Google Gemini API + Transformers (fallback)

- **Estilo:** Diseño responsivo con CSS puro

## Solución de Problemas

**No carga Gemini:** Verifica que configuraste la API Key correctamente en tu entorno.

**Falla la API:** El bot seguirá funcionando en modo fallback (modelo local).

**Puerto ocupado:** Cambia el puerto al iniciar Flask:
```bash 
flask run -p 5001
```
