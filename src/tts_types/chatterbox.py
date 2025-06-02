from src.logging import logging
logging.info("Importing chatterbox.py...")
import src.tts_types.base_tts as base_tts
try:
    logging.info("Trying to import chatterbox")
    from libraries.chatterbox.tts import ChatterboxTTS
    from libraries.chatterbox.vc import ChatterboxVC
    import random
    import numpy as np
    import torch
    import torchaudio as ta
    import os
    logging.info("Imported chatterbox")
except Exception as e:
    logging.error(f"Failed to import torch and torchaudio: {e}")
    raise e
logging.info("Imported required libraries in chatterbox.py")

tts_slug = "chatterbox"
class Synthesizer(base_tts.base_Synthesizer):
    def __init__(self, conversation_manager, ttses = []):
        super().__init__(conversation_manager)
        self.tts_slug = tts_slug
        logging.info(f"Initializing {self.tts_slug}...")

        self.model = None  # Initialize model as None
        self.model_type = "tts"  # Default model type
        self.get_or_load_tts_model() # Load TTS model on startup

        logging.info(f'{self.tts_slug} speaker wavs folders: {self.speaker_wavs_folders}')
        logging.config(f'{self.tts_slug} - Available voices: {self.voices()}')
        if len(self.voices()) > 0:
            random_voice = random.choice(self.voices())
            self._say("Chatterbox is ready to go.", random_voice)

    def get_or_load_tts_model(self):
        """Loads the ChatterboxTTS model if it hasn't been loaded already,
        and ensures it's on the correct device."""
        if self.model is None or self.model_type != "tts":
            self.model_type = "tts"
            print("TTS Model not loaded, initializing...")
            try:
                self.model = ChatterboxTTS.from_pretrained(self.config.chatterbox_device)
                if hasattr(self.model, 'to') and str(self.model.device) != self.config.chatterbox_device:
                    self.model.to(self.config.chatterbox_device)
                print(f"Model loaded successfully. Internal device: {getattr(self.model, 'device', 'N/A')}")
            except Exception as e:
                print(f"Error loading model: {e}")
                raise
            
    def get_or_load_vc_model(self):
        if self.model is None or self.model_type != "vc":
            self.model_type = "vc"
            print("VC Model not loaded, initializing...")
            try:
                self.model = ChatterboxVC.from_pretrained(self.config.chatterbox_device)
                if hasattr(self.model, 'to') and str(self.model.device) != self.config.chatterbox_device:
                    self.model.to(self.config.chatterbox_device)
                print(f"Model loaded successfully. Internal device: {getattr(self.model, 'device', 'N/A')}")
            except Exception as e:
                print(f"Error loading model: {e}")
                raise

    def voices(self):
        """Return a list of available voices"""
        voices = []
        for speaker_wavs_folder in self.speaker_wavs_folders:
            for speaker_wav_file in os.listdir(speaker_wavs_folder):
                speaker = speaker_wav_file.split(".")[0]
                if speaker_wav_file.endswith(".wav") and speaker not in voices:
                    voices.append(speaker)
        for banned_voice in self.config.chatterbox_banned_voice_models:
            if banned_voice in voices:
                voices.remove(banned_voice)
        return voices
    
    @property
    def default_voice_model_settings(self):
        return {
            "exaggeration": self.config.chatterbox_default_exaggeration,
            "temperature": self.config.chatterbox_default_temperature,
            "cfgw": self.config.chatterbox_default_cfgw,
        }
    
    def _synthesize(self, voiceline, voice_model, voiceline_location, aggro=0):
        """Synthesize the audio for the character specified using ParlerTTS"""
        logging.output(f'{self.tts_slug} - synthesizing {voiceline} with voice model "{voice_model}"...')
        speaker_wav_path = self.get_speaker_wav_path(voice_model)
        settings = self.voice_model_settings(voice_model)
        logging.output(f'{self.tts_slug} - using voice model settings: {settings}')
        if not voiceline.endswith(".") and not voiceline.endswith("!") and not voiceline.endswith("?"): # Add a period to the end of the voiceline if it doesn't have one. StyleTTS2 will make a strange blip sound if the voiceline doesn't end with a period.
            voiceline += "."
        
        if self.model is None:
            raise RuntimeError("TTS model is not loaded.")

        wav = self.model.generate(
            voiceline,
            batch_size=self.config.chatterbox_batch_size,
            batch_type=self.config.chatterbox_batch_type.lower(),
            audio_prompt_path=speaker_wav_path,
            exaggeration=settings['exaggeration'],
            temperature=settings['temperature'],
            cfg_weight=settings['cfgw'],
            max_tokens=self.config.chatterbox_max_tokens,  # Limit to 300 characters
            watermark=self.config.chatterbox_watermark,
        )         
        # Save the wav file
        wav = wav * self.config.chatterbox_volume
        ta.save(voiceline_location, wav, self.model.sr)
        logging.output(f'{self.tts_slug} - synthesized {voiceline} with voice model "{voice_model}"')