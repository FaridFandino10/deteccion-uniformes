from flask import Flask, request, render_template
from utils import UniformDetector
import os
from werkzeug.utils import secure_filename
import time
from datetime import datetime

app = Flask(__name__)

# Configuración de subida y validación de imágenes
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}
MAX_CONTENT_LENGTH = 4 * 1024 * 1024  # 4MB
app.config['UPLOAD_FOLDER'] = 'images/'
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

detector = UniformDetector('config.json')

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def limpiar_imagenes_antiguas(folder, dias=7):
    ahora = time.time()
    for filename in os.listdir(folder):
        filepath = os.path.join(folder, filename)
        if os.path.isfile(filepath):
            if ahora - os.path.getmtime(filepath) > dias * 86400:
                os.remove(filepath)

@app.route('/', methods=['GET'])
def index():
    error = request.args.get('error', '')
    return render_template('index.html', error=error)

@app.route('/detect', methods=['POST'])
def detect_uniform():
    print("\n" + "="*60)
    print("NUEVA DETECCION")
    print("="*60)
    
    aliado = request.form.get('aliado', '').strip()
    nombre_tecnico = request.form.get('nombre_tecnico', '').strip()
    uniforme_file = request.files.get('uniforme')

    print(f"Aliado: {aliado}")
    print(f"Tecnico: {nombre_tecnico}")

    # Validación de campos de texto
    if not aliado:
        return render_template('index.html', error="Debes ingresar el nombre del aliado.")
    if not nombre_tecnico:
        return render_template('index.html', error="Debes ingresar el nombre del técnico.")
    if len(nombre_tecnico) > 100 or len(aliado) > 100:
        return render_template('index.html', error="El nombre del técnico o aliado es demasiado largo.")

    # Validación de archivo
    if not uniforme_file or uniforme_file.filename == '':
        return render_template('index.html', error="No se envió la foto del uniforme.")
    if not allowed_file(uniforme_file.filename):
        return render_template('index.html', error="Solo se permiten imágenes JPG, JPEG o PNG.")

    uniforme_filename = secure_filename(uniforme_file.filename)
    uniforme_path = os.path.join(app.config['UPLOAD_FOLDER'], uniforme_filename)

    # Limpieza de imágenes antiguas antes de guardar
    limpiar_imagenes_antiguas(app.config['UPLOAD_FOLDER'])

    try:
        uniforme_file.save(uniforme_path)
        print(f"Imagen guardada: {uniforme_path}")
    except Exception as e:
        print(f"Error guardando imagen: {e}")
        return render_template('index.html', error=f"No se pudo guardar la imagen: {str(e)}")

    try:
        # Detectar elementos
        print("Detectando elementos...")
        detections = detector.detect_uniform_elements(uniforme_path)
        
        if not detections or detections.get('total_detections', 0) == 0:
            print("No se detectaron elementos")
            return render_template('index.html', error="No se detectaron elementos del uniforme.")
        
        print(f"Detectados: {detections.get('total_detections', 0)} elementos")
        
        # Calcular cumplimiento
        porcentaje, elementos_encontrados, elementos_faltantes = detector.calculate_compliance(
            detections.get('detected_elements', [])
        )
        
        print(f"Porcentaje: {porcentaje}%")
        print(f"Encontrados: {elementos_encontrados}")
        print(f"Faltantes: {elementos_faltantes}")
        
        # Guardar en Excel
        timestamp = datetime.now()
        print(f"\nGuardando en Excel...")  # noqa: F541
        
        detector.save_to_excel(
            nombre_tecnico, 
            elementos_encontrados, 
            elementos_faltantes, 
            porcentaje, 
            timestamp, 
            aliado
        )
        # Intentar guardar en Google Sheets y mostrar errores en logs
        try:
            detector.save_to_google_sheets(nombre_tecnico, elementos_encontrados, elementos_faltantes, porcentaje, timestamp, aliado)
            print("GUARDADO EXITOSO EN GOOGLE SHEETS")
        except Exception as e:
            print(f"ERROR AL GUARDAR EN GOOGLE SHEETS: {e}")
        
        print("="*60 + "\n")
        
        # Renderizar resultados
        return render_template('results.html',
            aliado=aliado,
            nombre=nombre_tecnico,
            porcentaje=porcentaje,
            detectados=', '.join(elementos_encontrados) if elementos_encontrados else 'Ninguno',
            faltantes=', '.join(elementos_faltantes) if elementos_faltantes else 'Ninguno',
            fecha=timestamp.strftime('%Y-%m-%d %H:%M:%S')
        )
        
    except Exception as e:
        print(f"ERROR GENERAL: {e}")
        import traceback
        traceback.print_exc()
        return render_template('index.html', error=f"Error: {str(e)}")

if __name__ == '__main__':
    print("Iniciando servidor Flask...")
    print(f"Directorio actual: {os.getcwd()}")
    app.run(host='0.0.0.0', port=5000, debug=True)