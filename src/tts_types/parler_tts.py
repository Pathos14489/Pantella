from src.logging import logging
logging.info("Importing parler_tts.py...")
import src.tts_types.base_tts as base_tts
try:
    logging.info("Trying to import torch")
    import torch
    logging.info("Imported torch and torchaudio")
except Exception as e:
    logging.error(f"Failed to import torch and torchaudio: {e}")
    raise e
try:
    logging.info("Trying to import ParlerTTS")
    from parler_tts import ParlerTTSForConditionalGeneration
    logging.info("Imported ParlerTTS")
except Exception as e:
    logging.error(f"Failed to import ParlerTTS: {e}")
    raise e
try:
    logging.info("Trying to import Tokenizer from transformers")
    from transformers import AutoTokenizer
    logging.info("Imported Tokenizer from transformers")
except Exception as e:
    logging.error(f"Failed to import av and AudioResampler: {e}")
    raise e
from pathlib import Path
import numpy as np
import os
import json
import io
import copy
import soundfile as sf
logging.info("Imported required libraries in chat_tts.py")

tts_slug = "parler_tts"
class Synthesizer(base_tts.base_Synthesizer):
    def __init__(self, conversation_manager, ttses = []):
        super().__init__(conversation_manager)
        self.tts_slug = tts_slug
        logging.info(f"Initializing {self.tts_slug}({self.config.parler_tts_model}) to device {self.config.parler_tts_device}")
        self.model = ParlerTTSForConditionalGeneration.from_pretrained(self.config.parler_tts_model).to(self.config.parler_tts_device)
        self.tokenizer = AutoTokenizer.from_pretrained(self.config.parler_tts_model)
        
        if self.config.parler_tts_compile:
            logging.info(f'Compiling {self.tts_slug} model...')
            self.model.generation_config.cache_implementation = "static"
            self.model.forward = torch.compile(self.model.forward, mode=self.config.parler_tts_compile_mode)
            logging.info(f'{self.tts_slug} model compiled successfully')

            inputs = self.tokenizer("This is for compilation", return_tensors="pt", padding="max_length", max_length=self.config.parler_tts_max_length).to(self.config.parler_tts_device)
            model_kwargs = {**inputs, "prompt_input_ids": inputs.input_ids, "prompt_attention_mask": inputs.attention_mask, }

            logging.info(f'Warming up {self.tts_slug} model...')
            n_steps = 1 if self.config.parler_tts_compile_mode == "script" else 2
            for _ in range(n_steps):
                _ = self.model.generate(**model_kwargs)
            logging.info(f'{self.tts_slug} model warmed up successfully')

        self._voices = None
        self.speaker_embeddings = {}
        logging.info(f'{self.tts_slug} speaker wavs folders: {self.voice_settings_folders}')
        logging.config(f'{self.tts_slug} - Available voices: {self.voices()}')
        if len(self.voices()) > 0:
            random_voice = np.random.choice(self.voices())
            self._say("Parler is ready to go.",random_voice)

    @property
    def voice_settings_folders(self):
        if "language" in self.config.__dict__:
            voice_settings_folders = [
                os.path.abspath(f".\\data\\parler_tts_inference_settings\\{self.language['tts_language_code']}\\")
            ]
        else:
            voice_settings_folders = []
            for language_code in os.listdir(".\\data\\parler_tts_inference_settings\\"):
                if not os.path.isdir(f".\\data\\parler_tts_inference_settings\\{language_code}\\"):
                    continue
                voice_settings_folders.append(os.path.abspath(f".\\data\\parler_tts_inference_settings\\{language_code}\\"))
        for addon_slug in self.config.addons:
            addon = self.config.addons[addon_slug]
            if "speakers" in addon["addon_parts"]:
                addon_speaker_wavs_folder = self.config.addons_dir + addon_slug + "\\parler_tts_inference_settings\\"
                if os.path.exists(addon_speaker_wavs_folder):
                    voice_settings_folders.append(addon_speaker_wavs_folder)
                else:
                    logging.error(f'speakers folder not found at: {addon_speaker_wavs_folder}')
        # make all the paths absolute
        voice_settings_folders = [os.path.abspath(folder) for folder in voice_settings_folders]
        return voice_settings_folders

    def voices(self):
        """Return a list of available voices"""
        if self._voices == None:
            voices = []
            for speaker_wavs_folder in self.voice_settings_folders:
                for file in os.listdir(speaker_wavs_folder):
                    if file.endswith(".json"):
                        with open(os.path.join(speaker_wavs_folder, file), 'r', encoding="utf8") as f:
                            json_data = json.load(f)
                            json_data['voice_model'] = file.replace(".json", "")
                            voices.append(json_data)
            self._voices = voices
        return [voice["voice_model"] for voice in self._voices]
        
    def get_voice_model_data(self, voice_model):
        """Return the voice model data for the specified voice model"""
        if self._voices == None:
            self.voices()
        for voice in self._voices:
            if voice["voice_model"] == voice_model:
                return voice
        return None
    
    def _synthesize(self, voiceline, voice_model, voiceline_location, aggro=0):
        """Synthesize the audio for the character specified using ParlerTTS"""
        logging.output(f'{self.tts_slug} - Loading voice model settings for {voice_model}')
        voice_model_settings = self.get_voice_model_data(voice_model)
        input_ids = self.tokenizer(voice_model_settings['description'], return_tensors="pt").input_ids.to(self.config.parler_tts_device)
        voiceline_input_ids = self.tokenizer(voiceline, return_tensors="pt").input_ids.to(self.config.parler_tts_device)

        generation = self.model.generate(
            input_ids=input_ids,
            prompt_input_ids=voiceline_input_ids,
            temperature= voice_model_settings['temperature'] if 'temperature' in voice_model_settings else self.config.parler_temperature,
        )
        audio_arr = generation.cpu().numpy().squeeze()
        sf.write(voiceline_location, audio_arr, self.model.config.sampling_rate)
