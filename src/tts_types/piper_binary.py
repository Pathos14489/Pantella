print("Loading piper_binary.py...")
from src.logging import logging
import src.tts_types.base_tts as base_tts
import os
import json
import numpy as np
logging.info("Imported required libraries in piper_binary.py")

tts_slug = "piper_binary"
class Synthesizer(base_tts.base_Synthesizer):
    def __init__(self, conversation_manager, ttses = []):
        super().__init__(conversation_manager)
        self.tts_slug = tts_slug
        self._voice_model_jsons = []
        logging.config(f"Loading piper_binary voices for game_id '{self.config.game_id}' from {self.piper_models_dir}{self.config.game_id}\\")
        for file in os.listdir(self.piper_models_dir+self.config.game_id+"\\"):
            if file.endswith(".json"):
                with open(self.piper_models_dir+self.config.game_id+"\\"+file, 'r', encoding="utf8") as f:
                    json_data = json.load(f)
                    json_data['model_name'] = file.replace(".onnx.json", "")
                    self._voice_model_jsons.append(json_data)

        logging.config(f'Available piper voices: {self.voices()}')
        if len(self.voices()) > 0:
            random_voice = np.random.choice(self.voices())
            self._say("Piper T T S is ready to go.",random_voice)

    @property
    def piper_binary_dir(self):
        return self.conversation_manager.config.piper_binary_dir
    
    @property
    def piper_models_dir(self):
        return self.conversation_manager.config.piper_models_dir

    def voices(self):
        """Return a list of available voices"""
        voices = []
        for voice_model in self._voice_model_jsons:
            voices.append(voice_model['model_name'])
        for banned_voice in self.config.piper_tts_banned_voices:
            if banned_voice in voices:
                voices.remove(banned_voice)
        return voices
    
    def _synthesize(self, voiceline, voice_model, voiceline_location, aggro=0):
        """Synthesize the audio for the character specified using piper"""
        # make sure directory exists
        os.makedirs(os.path.dirname(voiceline_location), exist_ok=True)
        command = f"echo \"{voiceline}\" | {self.piper_binary_dir}piper.exe --model {self.piper_models_dir}{self.config.game_id}\\{voice_model.lower()}.onnx --output_file {voiceline_location}"
        logging.output(f"piperTTS - Synthesizing voiceline: {voiceline}")
        logging.config(f"piperTTS - Synthesizing voiceline with command: {command}")
        os.system(command)