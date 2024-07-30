print('Loading openai_whisper.py...')
from src.logging import logging
import src.utils as utils
import requests
import json
logging.info('Imported required libraries in stt.py')

stt_slug = "openai_whisper"

class Transcriber:
    def __init__(self, game_interface):
        global stt_slug
        super().__init__(game_interface)
        self.stt_slug = stt_slug
        self.whisper_url = self.config.whisper_url
    
    @utils.time_it
    def whisper_transcribe(self, audio, prompt=None):
        logging.info('Transcribing audio using whisper...')
        url = self.whisper_url
        with open(self.config.secret_key_file_path, 'r') as f:
            api_key = f.readline().strip()
        if 'openai' in url:
            headers = {"Authorization": f"Bearer {api_key}",}
        else:
            logging.warn('Whisper URL not set to OpenAI API. If you are using a custom whisper server, please ensure the server is running and the URL is correct in config.json.')
            headers = {"Authorization": f"Bearer {api_key}",}
        data = {'model': self.config.whisper_model}
        files = {'file': open(audio, 'rb')}
        response = requests.post(url, headers=headers, files=files, data=data)
        response_data = json.loads(response.text)
        if 'text' in response_data:
            return response_data['text'].strip()