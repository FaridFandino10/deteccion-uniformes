#!/usr/bin/env python3
"""
Sistema de Detección de Uniforme de Técnicos - UTILS
VERSIÓN FINAL CORREGIDA
"""

import cv2
import os
import pandas as pd
from datetime import datetime
import json
from pathlib import Path
import shutil

# Importaciones para Roboflow
try:
    from roboflow import Roboflow
    ROBOFLOW_AVAILABLE = True
except ImportError:
    ROBOFLOW_AVAILABLE = False
    print("⚠️ Roboflow no disponible. Instala: pip install roboflow")

# Importaciones para OCR
try:
    import pytesseract
    from PIL import Image
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False
    print("⚠️ Tesseract no disponible. Instala: pip install pytesseract pillow")


class UniformDetector:
    """
    Clase principal para la detección de uniformes y identificación de técnicos
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
        
        # Verificar si /data existe (Render con disco) o usar raíz
        if os.path.exists("/data") and os.access("/data", os.W_OK):
            self.results_file = "/data/resultados_uniformes.xlsx"
            print("✅ Usando disco persistente en /data")
        else:
            self.results_file = "resultados_uniformes.xlsx"
            print("⚠️ Usando directorio raíz (sin persistencia)")
        
        self.setup_directories()
        
        # Cargar modelo si Roboflow está disponible
        if ROBOFLOW_AVAILABLE:
            self.load_model()
        else:
            print("⚠️ Roboflow no disponible. El modelo no se cargará.")
        
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
            print(f"⚠️ Config no encontrado. Creando {config_file}...")
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(default_config, f, indent=4, ensure_ascii=False)
            return default_config
        except json.JSONDecodeError as e:
            print(f"⚠️ Error en JSON: {e}. Usando config por defecto...")
            return default_config
    
    def setup_directories(self):
        """Crea los directorios necesarios para el proyecto"""
        directories = ["images", "results", "models"]
        for directory in directories:
            try:
                Path(directory).mkdir(exist_ok=True)
            except Exception as e:
                print(f"⚠️ No se pudo crear directorio {directory}: {e}")
        
        # Intentar crear /data si no existe
        if not os.path.exists("/data"):
            try:
                Path("/data").mkdir(exist_ok=True)
            except:  # noqa: E722
                pass
    
    def load_model(self):
        """Carga el modelo YOLOv11 desde Roboflow"""
        if not ROBOFLOW_AVAILABLE:
            print("❌ Roboflow no instalado")
            return False
            
        try:
            rf = Roboflow(api_key=self.config["roboflow"]["api_key"])
            project = rf.workspace(self.config["roboflow"]["workspace"]).project(
                self.config["roboflow"]["project"]
            )
            self.model = project.version(self.config["roboflow"]["version"]).model
            print("✅ Modelo YOLOv11 cargado desde Roboflow")
            return True
        except Exception as e:
            print(f"❌ Error al cargar modelo: {e}")
            return False
    
    def detect_uniform_elements(self, image_path):
        """Detecta elementos del uniforme usando YOLOv11"""
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Imagen no encontrada: {image_path}")

        if not image_path.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp')):
            raise ValueError("Formato no válido. Use JPG, JPEG, PNG o BMP.")

        if self.model is None:
            print("❌ Modelo no disponible")
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
            print(f"❌ Error en detección: {e}")
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
    
    def _crear_excel_inicial(self, filename):
        """Crea un archivo Excel con la estructura inicial"""
        df_inicial = pd.DataFrame(columns=[
            "Fecha", "Aliado", "Nombre", 
            "Tiene del uniforme", "Le falta tener", "Porcentaje"
        ])
        try:
            df_inicial.to_excel(filename, index=False, engine='openpyxl')
            print(f"📄 Archivo Excel inicial creado: {filename}")
            return True
        except Exception as e:
            print(f"❌ Error creando Excel inicial: {e}")
            return False
    
    def save_to_excel(self, nombre, elementos_encontrados, elementos_faltantes, 
                      porcentaje, timestamp, aliado="Sin especificar"):
        """
        Guarda los resultados en archivo Excel consolidado
        VERSIÓN FINAL - Compatible con y sin disco persistente
        """
        filename = self.results_file
        
        try:
            # Crear el nuevo registro
            nuevo_registro = pd.DataFrame([{
                "Fecha": timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                "Aliado": str(aliado),
                "Nombre": str(nombre),
                "Tiene del uniforme": ", ".join(elementos_encontrados) if elementos_encontrados else "Ninguno",
                "Le falta tener": ", ".join(elementos_faltantes) if elementos_faltantes else "Completo",
                "Porcentaje": f"{porcentaje:.1f}%"
            }])
            
            # Si el archivo no existe, crearlo
            if not os.path.exists(filename):
                # Buscar archivo en raíz del repo
                repo_file = "resultados_uniformes.xlsx"
                if os.path.exists(repo_file) and filename != repo_file:
                    try:
                        shutil.copy(repo_file, filename)
                        print(f"📋 Archivo copiado de repo a {filename}")
                    except Exception as e:
                        print(f"⚠️ No se pudo copiar: {e}")
                        self._crear_excel_inicial(filename)
                else:
                    self._crear_excel_inicial(filename)
            
            # Leer datos existentes
            if os.path.exists(filename):
                try:
                    df_existente = pd.read_excel(filename, engine='openpyxl')
                    df_final = pd.concat([df_existente, nuevo_registro], ignore_index=True)
                except Exception as e:
                    print(f"⚠️ Error leyendo archivo: {e}")
                    # Crear backup si hay error
                    try:
                        backup = filename.replace('.xlsx', f'_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx')
                        shutil.copy(filename, backup)
                        print(f"📦 Backup: {backup}")
                    except:  # noqa: E722
                        pass
                    df_final = nuevo_registro
            else:
                df_final = nuevo_registro
            
            # Guardar
            df_final.to_excel(filename, index=False, engine='openpyxl')
            
            # Verificar
            if os.path.exists(filename):
                file_size = os.path.getsize(filename)
                print(f"✅ Guardado en {filename} ({len(df_final)} registros, {file_size} bytes)")
                return True
            else:
                print("❌ El archivo no se creó")
                return False
                
        except PermissionError:
            print(f"❌ Sin permisos de escritura en {filename}")
            return False
        except Exception as e:
            print(f"❌ Error guardando: {e}")
            import traceback
            traceback.print_exc()
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
            print(f"❌ Error en OCR: {e}")
            return "Error en OCR"