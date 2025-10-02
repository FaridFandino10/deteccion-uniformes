#!/usr/bin/env python3
"""
Sistema de Detección de Uniforme de Técnicos - UTILS
====================================================

Archivo de utilidades con integración a Google Sheets usando Service Account
"""

import cv2
import os
import pandas as pd
from datetime import datetime
import json
from pathlib import Path

# Importaciones para Google Sheets con Service Account
try:
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
    GOOGLE_SHEETS_AVAILABLE = True
except ImportError:
    GOOGLE_SHEETS_AVAILABLE = False
    print("Google Sheets no disponible. Instala: pip install google-auth google-api-python-client")

# Importaciones para Roboflow
try:
    from roboflow import Roboflow
    ROBOFLOW_AVAILABLE = True
except ImportError:
    ROBOFLOW_AVAILABLE = False
    print("Roboflow no disponible. Instala: pip install roboflow")

# Importaciones para OCR
try:
    import pytesseract
    from PIL import Image
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False
    print("Tesseract no disponible. Instala: pip install pytesseract pillow")


class UniformDetector:
    """
    Clase principal para la detección de uniformes con integración a Google Sheets
    """
    
    def __init__(self, config_file="config.json"):
        """
        Inicializa el detector con configuración desde archivo JSON
        
        Args:
            config_file (str): Ruta al archivo de configuración
        """
        self.config = self.load_config(config_file)
        self.model = None
        self.uniform_elements = [
            "botas", "gafas", "guantes", "casco", 
            "camisa", "polo", "pantalon", "carnet"
        ]
        self.results_file = "resultados_uniformes.xlsx"
        self.setup_directories()
        
        # Cargar modelo si Roboflow está disponible
        if ROBOFLOW_AVAILABLE:
            self.load_model()
        else:
            print("Roboflow no disponible. El modelo no se cargará.")
        
    def load_config(self, config_file):
        """Carga la configuración desde un archivo JSON"""
        default_config = {
            "roboflow": {
                "api_key": "dy8yEoOuZlP1vRAPsNn0",
                "workspace": "regional-vmaxa",
                "project": "tecnicos-lcfxu",
                "version": 2
            },
            "tesseract": {
                "path": r"C:\Program Files\Tesseract-OCR\tesseract.exe",
                "config": "--oem 3 --psm 6"
            },
            "detection": {
                "confidence_threshold": 0.5,
                "nms_threshold": 0.4
            },
            "google_sheets": {
                "spreadsheet_id": "1F0XQM8Q9kn6uXs0KGgRETi_33iyQobGYPkHorav5ehw",
                "sheet_name": "Registros",
                "service_account_file": "credentials/service-account.json"
            }
        }
        
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
            merged_config = default_config.copy()
            for key, value in config.items():
                if isinstance(value, dict) and key in merged_config:
                    merged_config[key].update(value)
                else:
                    merged_config[key] = value
            return merged_config
        except FileNotFoundError:
            print(f"Config no encontrado. Creando {config_file}...")
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(default_config, f, indent=4, ensure_ascii=False)
            return default_config
        except json.JSONDecodeError as e:
            print(f"Error en JSON: {e}. Usando config por defecto...")
            return default_config
    
    def setup_directories(self):
        """Crea los directorios necesarios para el proyecto"""
        directories = ["images", "results", "models", "credentials"]
        for directory in directories:
            Path(directory).mkdir(exist_ok=True)
    
    def load_model(self):
        """Carga el modelo YOLOv11 desde Roboflow"""
        if not ROBOFLOW_AVAILABLE:
            print("Roboflow no instalado")
            return False
            
        try:
            rf = Roboflow(api_key=self.config["roboflow"]["api_key"])
            project = rf.workspace(self.config["roboflow"]["workspace"]).project(
                self.config["roboflow"]["project"]
            )
            self.model = project.version(self.config["roboflow"]["version"]).model
            print("Modelo YOLOv11 cargado desde Roboflow")
            return True
        except Exception as e:
            print(f"Error al cargar modelo: {e}")
            return False
    
    def detect_uniform_elements(self, image_path):
        """Detecta elementos del uniforme usando YOLOv11"""
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Imagen no encontrada: {image_path}")

        if not image_path.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp')):
            raise ValueError("Formato no válido. Use JPG, JPEG, PNG o BMP.")

        if self.model is None:
            print("Modelo no disponible")
            return {'detected_elements': [], 'carnet_box': None, 'total_detections': 0}

        image = cv2.imread(image_path)
        if image is None:
            raise ValueError("No se pudo leer la imagen.")

        try:
            prediction = self.model.predict(
                image_path, 
                confidence=self.config["detection"]["confidence_threshold"]
            )
            
            detected_elements = []
            carnet_box = None
            
            predictions = prediction.json().get('predictions', [])
            for detection in predictions:
                class_name = detection['class'].lower()
                confidence = detection['confidence']
                
                bbox = {
                    'x': detection['x'],
                    'y': detection['y'],
                    'width': detection['width'],
                    'height': detection['height'],
                    'confidence': confidence
                }
                
                detected_elements.append({
                    'element': class_name,
                    'confidence': confidence,
                    'bbox': bbox
                })
                
                if class_name == 'carnet' and carnet_box is None:
                    carnet_box = bbox
            
            return {
                'detected_elements': detected_elements,
                'carnet_box': carnet_box,
                'total_detections': len(detected_elements),
                'prediction_data': prediction.json()
            }
            
        except Exception as e:
            print(f"Error en detección: {e}")
            return {'detected_elements': [], 'carnet_box': None, 'total_detections': 0}
    
    def calculate_compliance(self, detected_elements):
        """Calcula el porcentaje de cumplimiento del uniforme"""
        detected_names = [elem['element'] for elem in detected_elements]
        elementos_encontrados = []
        
        for element in self.uniform_elements:
            if element in detected_names:
                elementos_encontrados.append(element)
        
        elementos_faltantes = [elem for elem in self.uniform_elements 
                              if elem not in elementos_encontrados]
        
        porcentaje = (len(elementos_encontrados) / len(self.uniform_elements)) * 100
        
        return porcentaje, elementos_encontrados, elementos_faltantes
    
    def get_google_sheets_service(self):
        """Obtiene el servicio de Google Sheets usando Service Account"""
        if not GOOGLE_SHEETS_AVAILABLE:
            print("Google Sheets API no disponible")
            return None
        
        try:
            # Intentar leer desde variable de entorno primero (para Render)
            service_account_json = os.environ.get('GOOGLE_SERVICE_ACCOUNT')
            
            if service_account_json:
                print("Usando credenciales desde variable de entorno")
                import json
                service_account_info = json.loads(service_account_json)
                credentials = service_account.Credentials.from_service_account_info(
                    service_account_info, 
                    scopes=['https://www.googleapis.com/auth/spreadsheets']
                )
            else:
                # Si no hay variable de entorno, usar archivo local
                print("Usando credenciales desde archivo local")
                service_account_file = self.config["google_sheets"]["service_account_file"]
                
                if not os.path.exists(service_account_file):
                    print(f"Archivo de service account no encontrado: {service_account_file}")
                    return None
                
                credentials = service_account.Credentials.from_service_account_file(
                    service_account_file, 
                    scopes=['https://www.googleapis.com/auth/spreadsheets']
                )
            
            service = build('sheets', 'v4', credentials=credentials)
            return service
            
        except Exception as e:
            print(f"Error creando servicio de Google Sheets: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def save_to_google_sheets(self, nombre, elementos_encontrados, elementos_faltantes, 
                              porcentaje, timestamp, aliado):
        """Guarda los resultados en Google Sheets usando Service Account"""
        if not GOOGLE_SHEETS_AVAILABLE:
            print("Google Sheets no disponible")
            return False
        
        try:
            service = self.get_google_sheets_service()
            if not service:
                print("No se pudo obtener servicio de Google Sheets")
                return False
            
            spreadsheet_id = self.config["google_sheets"]["spreadsheet_id"]
            sheet_name = self.config["google_sheets"]["sheet_name"]
            
            # Preparar datos
            values = [[
                timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                str(aliado),
                str(nombre),
                ", ".join(elementos_encontrados) if elementos_encontrados else "Ninguno",
                ", ".join(elementos_faltantes) if elementos_faltantes else "Completo",
                f"{porcentaje:.1f}%"
            ]]
            
            body = {'values': values}
            
            # Agregar datos
            result = service.spreadsheets().values().append(
                spreadsheetId=spreadsheet_id,
                range=f"{sheet_name}!A:F",
                valueInputOption='RAW',
                insertDataOption='INSERT_ROWS',
                body=body
            ).execute()
            
            print(f"Datos guardados en Google Sheets: {result.get('updates').get('updatedCells')} celdas")
            return True
            
        except Exception as e:
            print(f"Error guardando en Google Sheets: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def save_to_excel(self, nombre, elementos_encontrados, elementos_faltantes, 
                      porcentaje, timestamp, aliado="Sin especificar"):
        """Guarda los resultados en Excel local (respaldo)"""
        filename = "resultados_uniformes.xlsx"
        
        try:
            nuevo_registro = pd.DataFrame([{
                "Fecha": timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                "Aliado": str(aliado),
                "Nombre": str(nombre),
                "Tiene del uniforme": ", ".join(elementos_encontrados) if elementos_encontrados else "Ninguno",
                "Le falta tener": ", ".join(elementos_faltantes) if elementos_faltantes else "Completo",
                "Porcentaje": f"{porcentaje:.1f}%"
            }])
            
            if os.path.exists(filename):
                try:
                    df_existente = pd.read_excel(filename, engine='openpyxl')
                    df_final = pd.concat([df_existente, nuevo_registro], ignore_index=True)
                except Exception:
                    try:
                        backup = f"resultados_uniformes_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
                        os.rename(filename, backup)
                    except:  # noqa: E722
                        pass
                    df_final = nuevo_registro
            else:
                df_final = nuevo_registro
            
            df_final.to_excel(filename, index=False, engine='openpyxl')
            print(f"Registro guardado en Excel local (Total: {len(df_final)} registros)")
            return True
                
        except Exception as e:
            print(f"Error guardando en Excel: {e}")
            return False
    
    def extract_text_from_carnet(self, imagen_path, carnet_box=None):
        """Extrae texto del carnet usando OCR"""
        if not TESSERACT_AVAILABLE:
            return "OCR no disponible"
            
        try:
            tesseract_path = self.config["tesseract"]["path"]
            if os.path.exists(tesseract_path):
                pytesseract.pytesseract.tesseract_cmd = tesseract_path
            
            imagen_cv = cv2.imread(imagen_path)
            if imagen_cv is None:
                return "Error al cargar imagen"
                
            imagen_rgb = cv2.cvtColor(imagen_cv, cv2.COLOR_BGR2RGB)
            imagen_pil = Image.fromarray(imagen_rgb)

            if carnet_box:
                x = int(max(0, carnet_box['x'] - carnet_box['width'] / 2))
                y = int(max(0, carnet_box['y'] - carnet_box['height'] / 2))
                w = int(min(carnet_box['width'], imagen_pil.size[0] - x))
                h = int(min(carnet_box['height'], imagen_pil.size[1] - y))
                
                if w > 0 and h > 0:
                    imagen_pil = imagen_pil.crop((x, y, x + w, y + h))

            config = self.config["tesseract"]["config"]
            texto = pytesseract.image_to_string(imagen_pil, lang='spa', config=config)
            return texto.strip() if texto.strip() else "Texto no detectado"
            
        except Exception as e:
            print(f"Error en OCR: {e}")
            return "Error en OCR"