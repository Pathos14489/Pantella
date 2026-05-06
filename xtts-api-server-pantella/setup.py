from setuptools import setup, find_packages

setup(
    name='xtts_api_server',
    version='0.1.1',
    description='Mantella XTTS API Server',
    author='xyz',
    author_email='your.email@example.com',
    packages=find_packages(),
    install_requires=[
        'PyAudio==0.2.14',
        'requests==2.32.0',
        'pyttsx3==2.90',
        'stream2sentence==0.2.2',
        'fastapi>=0.104.1',
        'loguru',
        'pydantic',
        'pydub',
        'python-dotenv',
        'torch',
        'torchaudio',
        'uvicorn',
        'cutlet',
        'fugashi[unidic-lite]',
        'coqui-tts',
        'transformers==4.57.3',
        'uuid',
    ],
    entry_points={
        'console_scripts': [
            'xtts_api_server=xtts_api_server.__main__:run_server',
        ],
    },
)
