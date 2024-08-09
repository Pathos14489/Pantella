from src.logging import logging
logging.info("Importing style_tts_2.py...")
import src.tts_types.base_tts as base_tts
try:
    logging.info("Trying to import styletts2")
    from styletts2 import tts
    logging.info("Imported styletts2")
except Exception as e:
    logging.error(f"Failed to import torch and torchaudio: {e}")
    raise e
from pathlib import Path
import numpy as np
import os
import json
import io
import copy
import soundfile as sf
logging.info("Imported required libraries in style_tts_2.py")

tts_slug = "style_tts_2"
class Synthesizer(base_tts.base_Synthesizer):
    def __init__(self, conversation_manager, ttses = []):
        super().__init__(conversation_manager)
        self.tts_slug = tts_slug
        logging.info(f"Initializing {self.tts_slug}...")
        self.model = tts.StyleTTS2()

        logging.info(f'{self.tts_slug} speaker wavs folders: {self.speaker_wavs_folders}')
        logging.config(f'{self.tts_slug} - Available voices: {self.voices()}')
        if len(self.voices()) > 0:
            random_voice = np.random.choice(self.voices())
            self._say("Style T T S Two is ready to go.",random_voice)

    @property
    def speaker_wavs_folders(self):
        if "language" in self.config.__dict__:
            speaker_wavs_folders = [
                os.path.abspath(f".\\data\\voice_samples\\{self.language['tts_language_code']}\\")
            ]
        else:
            speaker_wavs_folders = []
            for language_code in os.listdir(".\\data\\voice_samples\\"):
                if not os.path.isdir(f".\\data\\voice_samples\\{language_code}\\"):
                    continue
                speaker_wavs_folders.append(os.path.abspath(f".\\data\\voice_samples\\{language_code}\\"))
        for addon_slug in self.config.addons:
            addon = self.config.addons[addon_slug]
            if "speakers" in addon["addon_parts"]:
                addon_speaker_wavs_folder = self.config.addons_dir + addon_slug + "\\speakers\\"
                if os.path.exists(addon_speaker_wavs_folder):
                    speaker_wavs_folders.append(addon_speaker_wavs_folder)
                else:
                    logging.error(f'speakers folder not found at: {addon_speaker_wavs_folder}')
        # make all the paths absolute
        speaker_wavs_folders = [os.path.abspath(folder) for folder in speaker_wavs_folders]
        return speaker_wavs_folders

    def voices(self):
        """Return a list of available voices"""
        voices = []
        for speaker_wavs_folder in self.speaker_wavs_folders:
            for speaker_wav_file in os.listdir(speaker_wavs_folder):
                speaker = speaker_wav_file.split(".")[0]
                if speaker_wav_file.endswith(".wav") and speaker not in voices:
                    voices.append(speaker)
        return voices
    
    def get_speaker_wav_path(self, voice_model):
        for speaker_wavs_folder in self.speaker_wavs_folders:
            speaker_wav_path = os.path.join(speaker_wavs_folder, f"{voice_model}.wav")
            if os.path.exists(speaker_wav_path):
                return speaker_wav_path
        return None
    
    def _synthesize(self, voiceline, voice_model, voiceline_location, aggro=0):
        """Synthesize the audio for the character specified using ParlerTTS"""
        logging.output(f'{self.tts_slug} - synthesizing {voiceline} with voice model "{voice_model}"...')
        speaker_wav_path = self.get_speaker_wav_path(voice_model)
        self.model.inference(voiceline, target_voice_path=speaker_wav_path, output_wav_file=voiceline_location)
        logging.output(f'{self.tts_slug} - synthesized {voiceline} with voice model "{voice_model}"')
        