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
import random
import os
import json
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
            random_voice = random.choice(self.voices())
            self._say("Style T T S Two is ready to go.",random_voice)

    @property
    def speaker_wavs_folders(self):
        if "language" in self.config.__dict__:
            if self.config.linux_mode:
                speaker_wavs_folders = [
                    os.path.abspath(f"./data/voice_samples/{self.language['tts_language_code']}/")
                ]
            else:
                speaker_wavs_folders = [
                    os.path.abspath(f".\\data\\voice_samples\\{self.language['tts_language_code']}\\")
                ]
        else:
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
        for addon_slug in self.config.addons:
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
        for banned_voice in self.config.style_tts_2_banned_voice_models:
            if banned_voice in voices:
                voices.remove(banned_voice)
        return voices
    
    def voice_model_settings(self, voice_model):
        # speaker voice model settings are stored in ./data/chat_tts_inference_settings/{tts_language_code}/{voice_model}.json
        settings = {
            "alpha": self.config.style_tts_2_default_alpha,
            "beta": self.config.style_tts_2_default_beta,
            "t": self.config.style_tts_2_default_t,
            "diffusion_steps": self.config.style_tts_2_default_diffusion_steps,
            "embedding_scale": self.config.style_tts_2_default_embedding_scale,
        }
        if self.config.linux_mode:
            voice_model_settings_path = os.path.abspath(f"./data/style_tts_2_inference_settings/{self.language['tts_language_code']}/{voice_model}.json")
        else:
            voice_model_settings_path = os.path.abspath(f".\\data\\style_tts_2_inference_settings\\{self.language['tts_language_code']}\\{voice_model}.json")
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
        if not voiceline.endswith(".") and not voiceline.endswith("!") and not voiceline.endswith("?"): # Add a period to the end of the voiceline if it doesn't have one. StyleTTS2 will make a strange blip sound if the voiceline doesn't end with a period.
            voiceline += "."
        self.model.inference(voiceline,
            target_voice_path=speaker_wav_path,
            output_wav_file=voiceline_location,
            alpha=settings["alpha"],
            beta=settings["beta"],
            # t=settings["t"],/\
            diffusion_steps=settings["diffusion_steps"],
            embedding_scale=settings["embedding_scale"]
        )
        logging.output(f'{self.tts_slug} - synthesized {voiceline} with voice model "{voice_model}"')