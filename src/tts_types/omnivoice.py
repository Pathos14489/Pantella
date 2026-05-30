from src.logging import logging
logging.info("Importing omnivoice.py...")
import src.tts_types.base_tts as base_tts
imported = False
try:
    logging.info("Trying to import omnivoice")
    import omnivoice as ov
    import random
    import torch as th
    import io
    import numpy as np
    import soundfile as sf
    imported = True
    logging.info("Imported omnivoice")
except Exception as e:
    logging.error(f"Failed to import omnivoice: {e}")
    raise e
logging.info("Imported required libraries in omnivoice.py")

tts_slug = "omnivoice"
tts_name = "Omnivoice"
default_settings = {
    "omnivoice_device": "cuda",
    "omnivoice_default_cfg": 2.0,
    "omnivoice_default_num_step": 32,
    "omnivoice_default_denoise": True,
    "omnivoice_volume": 1.0,
    "omnivoice_banned_voice_models": [],
}
settings_description = {
    "omnivoice_device": "The device to run the Omnivoice model on. This can be changed in your [game_id]_config.json. The default is 'cuda', but if you have a compatible NVIDIA GPU, you can set this to 'cuda' to significantly speed up synthesis times. If you don't have a compatible GPU, you can set this to 'cpu', but keep in mind that synthesis times will be significantly longer.",
    "omnivoice_default_temperature": "Temperature of the voice, higher values make the voice sound more random and less predictable. Can make voices less robotic and more human-like, but can also make them sound more unnatural and have glitches/artifacts.",
    "omnivoice_volume": "The volume of the generated audio. This can be used to increase or decrease the volume of the generated audio. The default is 1.0, which means no change in volume. Values greater than 1.0 will increase the volume, while values less than 1.0 will decrease the volume.",
    "omnivoice_banned_voice_models": "A list of voice models to ban from being used by Omnivoice. This can be changed in your [game_id]_config.json. This is useful if you have a voice model that causes issues with Omnivoice, such as extremely long synthesis times or crashes."
}
options = {}
settings = {}
loaded = False
description = "\"is a state-of-the-art massively multilingual zero-shot text-to-speech (TTS) model supporting over 600 languages. Built on a novel diffusion language model-style architecture, it generates high-quality speech with superior inference speed, supporting voice cloning and voice design.\" Exceptional quality, lower VRAM requirements than almost any other TTS model, runs slowly on CPU, runs way faster than real-time on GPU, overall exceptional model."
class Synthesizer(base_tts.base_Synthesizer):
    def __init__(self, conversation_manager, ttses = []):
        global tts_slug, default_settings, loaded
        super().__init__(conversation_manager)
        self.tts_slug = tts_slug
        self._default_settings = default_settings
        logging.info(f"Initializing {self.tts_slug}...")

        # choose device
        if th.cuda.is_available():
            device_map = "cuda:0"
            dtype = th.float16
        elif getattr(th, "has_mps", False) and getattr(th.backends, "mps", None) and th.backends.mps.is_available():
            device_map = "mps"
            dtype = th.float32
        else:
            device_map = "cpu"
            dtype = th.float32

        self.model = ov.OmniVoice.from_pretrained("k2-fsa/OmniVoice", device_map=device_map, dtype=dtype)
        self.gen_config = ov.OmniVoiceGenerationConfig(
            num_step=int(self.config.omnivoice_default_num_step or 32),
            guidance_scale=float(self.config.omnivoice_default_cfg or 2.0),
            denoise=bool(self.config.omnivoice_default_denoise)
            # preprocess_prompt=bool(preprocess_prompt),
            # postprocess_output=bool(postprocess_output),
        )
        self.needs_transcription = True

        logging.info(f'{self.tts_slug} speaker wavs folders: {self.speaker_wavs_folders}')
        logging.config(f'{self.tts_slug} - Available voices: {self.voices()}')
        if len(self.voices()) > 0:
            random_voice = random.choice(self.voices())
            self._say("OmniVoice is ready to go.", random_voice)
        loaded = True
        
    def unload(self):
        """Unload the TTS engine and free up any resources it's using. This is called when the TTS engine is changed or when Pantella is closed."""
        if self.model is not None:
            logging.info(f'Unloading {self.tts_slug} model to free up resources...')
            del self.model
            self.model = None
            logging.info(f'{self.tts_slug} model unloaded.')

    def voices(self):
        """Return a list of available voices"""
        voices = super().voices()
        for banned_voice in self.config.omnivoice_banned_voice_models:
            if banned_voice in voices:
                voices.remove(banned_voice)
        return voices
    
    @property
    def default_voice_model_settings(self):
        return {
            "transcription": "",
            "cfg": self.config.omnivoice_default_cfg,
            "num_step": self.config.omnivoice_default_num_step,
            "denoise": self.config.omnivoice_default_denoise,
        }

    def _synthesize(self, voiceline, voice_model, voiceline_location, settings, aggro=0):
        """Synthesize the audio for the character specified using ParlerTTS"""
        logging.output(f'{self.tts_slug} - synthesizing {voiceline} with voice model "{voice_model}"...')
        speaker_wav_path = self.get_speaker_wav_path(voice_model)
        logging.output(f'{self.tts_slug} - using voice model settings: {settings}')

        opts = {
            "ref_audio": speaker_wav_path,
            "ref_text": settings.get("transcription", self.default_voice_model_settings["transcription"]),
            "num_step": settings.get("num_step", self.default_voice_model_settings["num_step"]),
            "cfg": settings.get("cfg", self.default_voice_model_settings["cfg"]),
            "denoise": settings.get("denoise", self.default_voice_model_settings["denoise"]),
            "speed": settings.get("speed", 1.0),
            "gen_config": self.gen_config,
        }

        # Generate the audio using the model
        out = self.model.generate(text=voiceline, **opts)
        # Save the generated audio to a temporary file
        sf.write(voiceline_location, out[0], 24000, subtype='PCM_16')
        
        if self.model is None:
            raise RuntimeError("TTS model is not loaded.")
        logging.output(f'{self.tts_slug} - synthesized {voiceline} with voice model "{voice_model}"')