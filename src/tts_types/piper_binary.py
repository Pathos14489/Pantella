print("Loading piper_binary.py...")
from src.logging import logging
import src.tts_types.base_tts as base_tts
import os
import json
import random
logging.info("Imported required libraries in piper_binary.py")

tts_slug = "piper_binary"
default_settings = {
    "piper_binary_dir": ".\\piper\\",
    "piper_models_dir": ".\\data\\models\\piper\\",
    "piper_tts_banned_voice_models": [],
}
settings_description = {
    "piper_binary_dir": "The directory where the Piper binary is located. This can be changed in config.json. The default is '.\\piper\\', which means that the Piper binary should be located in a folder called 'piper' in the same directory as Pantella.",
    "piper_models_dir": "The directory where the Piper models are located. This can be changed in config.json. The default is '.\\data\\models\\piper\\', which means that the Piper models should be located in a folder called 'piper' inside the 'models' folder in the 'data' directory.",
    "piper_tts_banned_voice_models": "A list of voice models to ban from being used by PiperTTS. This can be changed in config.json. This is useful if you have a voice model that causes issues with PiperTTS, such as extremely long synthesis times or crashes."
}
options = {}
settings = {}
loaded = False
imported = True
description = "PiperTTS is a fast and really easy to run on most computers. It doesn't require special hardware like a CUDA enabled GPU and instead runs on CPU."
class Synthesizer(base_tts.base_Synthesizer):
    def __init__(self, conversation_manager, ttses = []):
        global tts_slug, default_settings, loaded
        super().__init__(conversation_manager)
        self.tts_slug = tts_slug
        self._default_settings = default_settings
        self._voice_model_jsons = []
        logging.config(f"Loading piper_binary voices for game_id '{self.config.game_id}' from {self.piper_models_dir}{self.config.game_id}\\")
        models_path = self.piper_models_dir+self.config.game_id+"\\"
        if self.config.linux_mode:
            models_path = models_path.replace("\\", "/")
        if not os.path.exists(models_path):
            logging.warning(f"Piper models directory for game_id '{self.config.game_id}' not found at {models_path}. No Piper voices will be loaded.")
            return
        for file in os.listdir(models_path):
            if file.endswith(".json"):
                with open(os.path.join(models_path, file), 'r', encoding="utf8") as f:
                    json_data = json.load(f)
                    json_data['model_name'] = file.replace(".onnx.json", "")
                    self._voice_model_jsons.append(json_data)

        logging.config(f'Available piper voices: {self.voices()}')
        if len(self.voices()) > 0:
            random_voice = random.choice(self.voices())
            self._say("Piper T T S is ready to go.",random_voice)
        loaded = True

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
        for banned_voice in self.config.piper_tts_banned_voice_models:
            if banned_voice in voices:
                voices.remove(banned_voice)
        return voices
    
    @property
    def default_voice_model_settings(self):
        return {}
    
    def _synthesize(self, voiceline, voice_model, voiceline_location, settings, aggro=0):
        """Synthesize the audio for the character specified using piper"""
        # make sure directory exists
        os.makedirs(os.path.dirname(voiceline_location), exist_ok=True)
        if self.config.linux_mode:
            command = f"echo \"{voiceline}\" | wine {self.piper_binary_dir}piper.exe --model {self.piper_models_dir}{self.config.game_id}/{voice_model.lower()}.onnx --output_file \"{voiceline_location}\""
        else:
            command = f"echo \"{voiceline}\" | {self.piper_binary_dir}piper.exe --model {self.piper_models_dir}{self.config.game_id}\\{voice_model.lower()}.onnx --output_file \"{voiceline_location}\""
        logging.output(f"piperTTS - Synthesizing voiceline: {voiceline}")
        logging.config(f"piperTTS - Synthesizing voiceline with command: {command}")
        os.system(command)