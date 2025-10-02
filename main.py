import argparse
from utils import UniformDetector

def main():
    """Función principal"""
    parser = argparse.ArgumentParser(description="Sistema de Detección de Uniformes")
    parser.add_argument("--image", "-i", type=str, help="Ruta a una imagen existente")
    parser.add_argument("--config", "-c", type=str, default="config.json", 
                       help="Archivo de configuración")
    
    args = parser.parse_args()
    
    try:
        # Crear detector
        detector = UniformDetector(args.config)
        
        # Ejecutar detección
        detector.run_detection(args.image)
        
    except KeyboardInterrupt:
        print("\n❌ Proceso interrumpido por el usuario")
    except Exception as e:
        print(f"❌ Error inesperado: {e}")


if __name__ == "__main__":
    main()