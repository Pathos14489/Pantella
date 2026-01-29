print("Loading mira_tts.py...")
from src.logging import logging
import src.tts_types.base_tts as base_tts
import os
import json
import random
logging.info("Imported required libraries in mira_tts.py")

try:
    logging.info("Trying to import mira_tts")
    from mira.model import MiraTTS
    from IPython.display import Audio
    imported = True
    logging.info("Imported mira_tts")
except Exception as e:
    logging.error(f"Failed to import mira_tts: {e}")
    raise e

tts_slug = "mira_tts"
default_settings = {}
settings_description = {}
options = {}
settings = {}
loaded = False
imported = True
description = "MiraTTS is a fast and really easy to run on most computers. It doesn't require special hardware like a CUDA enabled GPU and instead runs on CPU."
class Synthesizer(base_tts.base_Synthesizer):
    def __init__(self, conversation_manager, ttses = []):
        global tts_slug, default_settings, loaded
        super().__init__(conversation_manager)
        self.tts_slug = tts_slug
        self._default_settings = default_settings
        
        self.mira_tts = MiraTTS('YatharthS/MiraTTS') ## downloads model from huggingface
        
        logging.config(f'Available mira_tts voices: {self.voices()}')
        if len(self.voices()) > 0:
            random_voice = random.choice(self.voices())
            self._say("mira T T S is ready to go.",random_voice)
        loaded = True

    def voices(self):
        """Return a list of available voices"""
        voices = []
        voices = super().voices()
        for banned_voice in self.config.f5_tts_banned_voice_models:
            if banned_voice in voices:
                voices.remove(banned_voice)
        return voices
    
    @property
    def default_voice_model_settings(self):
        return {}
    
    def _synthesize(self, voiceline, voice_model, voiceline_location, settings, aggro=0):
        """Synthesize the audio for the character specified using mira_tts"""
        speaker_wav_path = self.get_speaker_wav_path(voice_model)
        context_tokens = self.mira_tts.encode_audio(speaker_wav_path)
        audio = self.mira_tts.generate(voiceline, context_tokens)
        audio = Audio(audio, rate=48000)
        # write to voiceline_location
        with open(voiceline_location, 'wb') as f:
            f.write(audio.data)