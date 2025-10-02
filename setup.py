
from setuptools import setup # type: ignore

setup(
    name='sistema_deteccion_uniformes',
    version='1.0',
    py_modules=['main', 'utils'],
    install_requires=[
        'opencv-python',
        'numpy',
        'pandas',
        'pytesseract',
        'roboflow',
        'google-api-python-client',
        'google-auth-httplib2',
        'google-auth-oauthlib',
        'openpyxl'
    ],
    entry_points={
        'console_scripts': [
            'detectar-uniforme = main:main'
        ]
    }
)
