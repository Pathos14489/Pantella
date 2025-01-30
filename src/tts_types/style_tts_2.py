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
    
    @property
    def default_voice_model_settings(self):
        return {
            "alpha": self.config.style_tts_2_default_alpha,
            "beta": self.config.style_tts_2_default_beta,
            "t": self.config.style_tts_2_default_t,
            "diffusion_steps": self.config.style_tts_2_default_diffusion_steps,
            "embedding_scale": self.config.style_tts_2_default_embedding_scale,
        }
    
    
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