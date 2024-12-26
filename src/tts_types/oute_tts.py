from src.logging import logging
logging.info("Importing outetts.py...")
import src.tts_types.base_tts as base_tts
try:
    logging.info("Trying to import outetts")
    import outetts
    logging.info("Imported outetts")
except Exception as e:
    logging.error(f"Failed to import torch and torchaudio: {e}")
    raise e
import random
import os
import json
import tempfile

import soundfile as sf
import torchaudio

logging.info("Imported required libraries in outetts.py")

tts_slug = "oute_tts"
class Synthesizer(base_tts.base_Synthesizer):
    def __init__(self, conversation_manager, ttses = []):
        super().__init__(conversation_manager)
        self.tts_slug = tts_slug
        logging.info(f"Initializing {self.tts_slug}...")
        self.model_config = outetts.HFModelConfig_v1(
            model_path="OuteAI/OuteTTS-0.2-500M",
            language="en",  # Supported languages in v0.2: en, zh, ja, ko
        )
        self.interface = outetts.InterfaceHF(model_version="0.2", cfg=self.model_config)

        logging.info(f'{self.tts_slug} speaker wavs folders: {self.speaker_wavs_folders}')
        logging.config(f'{self.tts_slug} - Available voices: {self.voices()}')
        if len(self.voices()) > 0:
            random_voice = random.choice(self.voices())
            self._say("Out Eee Tee Tee Ees is ready to go.",random_voice)

    @property
    def speaker_wavs_folders(self):
        if "language" in self.config.__dict__: # If the language is specified in the config, only use the speaker wavs folder for that language
            if self.config.linux_mode:
                speaker_wavs_folders = [
                    os.path.abspath(f"./data/voice_samples/{self.language['tts_language_code']}/")
                ]
            else:
                speaker_wavs_folders = [
                    os.path.abspath(f".\\data\\voice_samples\\{self.language['tts_language_code']}\\")
                ]
        else: # Otherwise, use all the speaker wavs folders
            speaker_wavs_folders = []
            if self.config.linux_mode:
                for language_code in os.listdir("./data/voice_samples/"):
                    if not os.path.isdir(f"./data/voice_samples/{language_code}/"):
                        continue
                    speaker_wavs_folders.append(os.path.abspath(f"./data/voice_samples/{language_code}/"))
            else:
                for language_code in os.listdir(".\\data\\voice_samples\\"):
                    if not os.path.isdir(f".\\data\\voice_samples\\{language_code}\\"):
                        continue
                    speaker_wavs_folders.append(os.path.abspath(f".\\data\\voice_samples\\{language_code}\\"))
        for addon_slug in self.config.addons: # Add the speakers folder from each addon to the list of speaker wavs folders
            addon = self.config.addons[addon_slug]
            if "speakers" in addon["addon_parts"]: 
                if self.config.linux_mode:
                    addon_speaker_wavs_folder = os.path.abspath(f"./addons/{addon_slug}/speakers/")
                else:
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
        for banned_voice in self.config.oute_tts_banned_voice_models:
            if banned_voice in voices:
                voices.remove(banned_voice)
        return voices
    
    def voice_model_settings(self, voice_model):
        # speaker voice model settings are stored in ./data/chat_tts_inference_settings/{tts_language_code}/{voice_model}.json
        settings = {
            "transcription": "",
            "temperature": 0.1,
            "repetition_penalty": 1.1,
        }
        if self.config.linux_mode:
            voice_model_settings_path = os.path.abspath(f"./data/oute_tts_inference_settings/{self.language['tts_language_code']}/{voice_model}.json")
        else:
            voice_model_settings_path = os.path.abspath(f".\\data\\oute_tts_inference_settings\\{self.language['tts_language_code']}\\{voice_model}.json")
        if os.path.exists(voice_model_settings_path):
            with open(voice_model_settings_path, "r") as f:
                voice_model_settings = json.load(f)
            for setting in settings:
                if setting in voice_model_settings:
                    settings[setting] = voice_model_settings[setting]
        return settings
    
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
        settings = self.voice_model_settings(voice_model)
        logging.output(f'{self.tts_slug} - using voice model settings: {settings}')
        if not voiceline.endswith(".") and not voiceline.endswith("!") and not voiceline.endswith("?"): # Add a period to the end of the voiceline if it doesn't have one.
            voiceline += "."
        speaker = self.interface.create_speaker(
            audio_path=speaker_wav_path,
            transcript=settings["transcription"]
        )
        temperature = settings["temperature"] if "temperature" in settings else self.config.oute_tts_temperature
        repetition_penalty = settings["repetition_penalty"] if "repetition_penalty" in settings else self.config.oute_tts_repetition_penalty
        max_length = self.config.oute_tts_max_length
        output = self.interface.generate(
            text=voiceline,
            # Lower temperature values may result in a more stable tone,
            # while higher values can introduce varied and expressive speech
            temperature=temperature,
            repetition_penalty=repetition_penalty,
            max_length=max_length,

            # Optional: Use a speaker profile for consistent voice characteristics
            # Without a speaker profile, the model will generate a voice with random characteristics
            speaker=speaker,
        )
        output.save(voiceline_location)
        logging.output(f'{self.tts_slug} - synthesized {voiceline} with voice model "{voice_model}"')