print("Loading chatterbox_api.py...")
from src.logging import logging
import src.utils as utils
import src.tts_types.base_tts as base_tts
import os
from pathlib import Path
import requests
import time
import subprocess
import threading
import traceback
import io
import random
logging.info("Imported required libraries in chatterbox_api.py")

tts_slug = "chatterbox_api"
default_settings = {
    "exaggeration": 0.5,
    "temperature": 0.5,
    "cfgw": 0.8,
}
settings_description = {
    "exaggeration": "The default settings (0.5) work well for most prompts. Higher exaggeration tends to speed up speech, reducing cfg_weight helps compensate with slower, more deliberate pacing.",
    "temperature": "Temperature of the voice, higher values make the voice sound more random and less predictable. Can make voices less robotic and more human-like, but can also make them sound more unnatural and have glitches/artifacts.",
    "cfgw": "If the reference speaker has a fast speaking style, lowering cfg_weight to around 0.3 can improve pacing.",
}
options = {}
settings = {}
loaded = False
imported = True
description = "is a \"production-grade open source TTS model. Licensed under MIT, Chatterbox has been benchmarked against leading closed-source systems like ElevenLabs, and is consistently preferred in side-by-side evaluations.\" Very good emotional tinting in speaking, can do a lot of different voices very well, and isn't unusably slow, though it is a bit slower than xTTS 2 on the same hardware. It needs 6GB of VRAM to run on GPU, but it can run on CPU as well, albiet, very slowly, about five times slower than the GPU(2080 ti) on a Ryzen 9 5950X with DDR4."
class Synthesizer(base_tts.base_Synthesizer): 
    def __init__(self, conversation_manager):
        global tts_slug, default_settings, loaded
        super().__init__(conversation_manager)
        self.tts_slug = tts_slug
        self._default_settings = default_settings
        logging.info(f'Chatterbox API speaker wavs folders: {self.speaker_wavs_folders}')
        if not self.is_running():
            logging.info(f'Waiting for Chatterbox_API server to start...')
            self.times_checked = 0
            while not self.is_running() and self.times_checked < 40:  # Check if Chatterbox_API is running
                time.sleep(2)  # Wait for Chatterbox_API server to start
                if self.times_checked == 20:
                    logging.error(f'chatterbox_API server is taking longer than expected to start. Please check the chatterbox_API server logs for any errors. Or your computer may be a bit slower than expected.')
                self.times_checked += 1
            if self.times_checked >= 20:
                logging.error(f'chatterbox_API server failed to start. Please check the chatterbox_API server logs for any errors.')
                input('\nPress any key to stop Pantella...')
                raise Exception(f'chatterbox_API server failed to start. Please check the chatterbox_API server logs for any errors.')
            
            logging.info(f'Chatterbox_API server is running!')
        else:
            logging.info(f'Chatterbox_API server is already running.')

        logging.config(f'chatterbox_api - Available chatterbox_api voices: {self.voices()}')
        if len(self.voices()) > 0:
            random_voice = random.choice(self.voices())
            self._say("Chatterbox API is ready to go.", random_voice)
        loaded = True

    @property
    def default_voice_model_settings(self):
        return {
            "exaggeration": self.config.chatterbox_api_default_exaggeration,
            "temperature": self.config.chatterbox_api_default_temperature,
            "cfgw": self.config.chatterbox_api_default_cfgw,
        }

    def voices(self):
        """Return a list of available voices"""
        voices = super().voices()
        for banned_voice in self.config.chatterbox_api_banned_voice_models:
            if banned_voice in voices:
                voices.remove(banned_voice)
        return voices
    
    def is_running(self):
        """Check if the Chatterbox server is running"""
        try:
            print("Checking if Chatterbox server is running...")
            response = requests.get(self.config.chatterbox_api_base_url+"/status")
            response.raise_for_status()  # If the response contains an HTTP error status code, 
            return True
        except:
            return False

    @utils.time_it
    def _synthesize(self, voiceline, voice_model, voiceline_location, settings, aggro=0):
        """Synthesize a line using the Chatterbox API"""
        global tts_slug, default_settings
        speaker_wav_path = self.get_speaker_wav_path(voice_model)
        speaker_wav_data = open(speaker_wav_path, 'rb').read()
        logging.output(f'{self.tts_slug} - synthesizing {voiceline} with voice model "{voice_model}"...')
        data = {
            'prompt': (None, voiceline),
            'voice_wav': (os.path.basename(speaker_wav_path), speaker_wav_data),
            "temperature": settings.get("temperature", self.default_voice_model_settings["temperature"]),
            "cfgw": settings.get("cfgw", self.default_voice_model_settings["cfgw"]),
            "exaggeration": settings.get("exaggeration", self.default_voice_model_settings["exaggeration"]),
        }

        # print(data)
        try:
            response = requests.post(self.config.chatterbox_api_base_url+"/synthesize", files=data)
            with open(Path(voiceline_location), 'wb') as f:
                f.write(response.content)
            if response.status_code == 200: # if the request was successful, write the wav file to disk at the specified path
                self.convert_to_16bit(io.BytesIO(response.content), voiceline_location)
            else:
                logging.error(f'Chatterbox API failed to generate voiceline at: {Path(voiceline_location)}')
                raise FileNotFoundError()
        except Exception as e:
            logging.error(f'Chatterbox API failed to generate voiceline at: {Path(voiceline_location)}')
            logging.error(e)
            raise FileNotFoundError()
        logging.output(f'{self.tts_slug} - synthesized {voiceline} with voice model "{voice_model}"')