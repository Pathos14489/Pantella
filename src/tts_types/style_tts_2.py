from src.logging import logging
logging.info("Importing style_tts_2.py...")
import src.tts_types.base_tts as base_tts
import random
import os
imported = False
try:
    logging.info("Trying to import styletts2")
    from styletts2 import tts
    imported = True
    logging.info("Imported styletts2")
except Exception as e:
    logging.error(f"Failed to import torch and torchaudio: {e}")
    raise e
logging.info("Imported required libraries in style_tts_2.py")

tts_slug = "style_tts_2"
default_settings = {
    "alpha": 0.3,
    "beta": 0.7,
    "diffusion_steps": 5,
    "embedding_scale": 1.0,
}
settings_description = {
    "alpha": "alpha and beta is the factor to determine much we use the style sampled based on the text instead of the reference. The higher the value of alpha and beta, the more suitable the style it is to the text but less similar to the reference. Alpha determines the timbre of the speaker. If alpha = 1 and beta = 1, the synthesized speech sounds the most dissimilar to the reference speaker, but it is also the most diverse (each time you synthesize a speech it will be totally different). If alpha = 0 and beta = 0, the synthesized speech sounds the most siimlar to the reference speaker, but it is deterministic (i.e., the sampled style is not used for speech synthesis).",
    "beta": "alpha and beta is the factor to determine much we use the style sampled based on the text instead of the reference. Using higher beta makes the synthesized speech more emotional, at the cost of lower similarity to the reference. Beta determines the prosody of the speaker.",
    "diffusion_steps": "The number of diffusion steps for the StyleTTS2 model. Higher values can clean up the audio, but also increase the time it takes to synthesize the audio. There is also a point of diminishing returns, where increasing the diffusion steps doesn't really improve the audio quality much.",
    "embedding_scale": "At value 1, this is the classifier-free guidance scale. The higher the scale, the more conditional the style is to the input text and hence more emotional."
}
options = {}
settings = {}
loaded = False
description = "StyleTTS2 is very similar to xTTS 2, but it's a bit more robotic sounding and has pronounciation issues sometimes. But higher pitch voices, like some of the female voices in Skyrim, sound a bit better with StyleTTS2 than xTTS 2. It's also a bit faster than xTTS 2, and doesn't require as much VRAM, hovering closer to 3GB of usage. It can be sampled on a short sample between 15-25 seconds with decent quality."
class Synthesizer(base_tts.base_Synthesizer):
    def __init__(self, conversation_manager, ttses = []):
        global tts_slug, default_settings, loaded
        super().__init__(conversation_manager)
        self.tts_slug = tts_slug
        self._default_settings = default_settings
        logging.info(f"Initializing {self.tts_slug}...")
        self.model = tts.StyleTTS2()

        logging.info(f'{self.tts_slug} speaker wavs folders: {self.speaker_wavs_folders}')
        logging.config(f'{self.tts_slug} - Available voices: {self.voices()}')
        if len(self.voices()) > 0:
            random_voice = random.choice(self.voices())
            self._say("Style T T S Two is ready to go.",random_voice)
        loaded = True

    def voices(self):
        """Return a list of available voices"""
        voices = super().voices()
        for banned_voice in self.config.style_tts_2_banned_voice_models:
            if banned_voice in voices:
                voices.remove(banned_voice)
        return voices
    
    @property
    def default_voice_model_settings(self):
        return {
            "alpha": self.config.style_tts_2_default_alpha,
            "beta": self.config.style_tts_2_default_beta,
            "diffusion_steps": self.config.style_tts_2_default_diffusion_steps,
            "embedding_scale": self.config.style_tts_2_default_embedding_scale,
        }
    
    
    def _synthesize(self, voiceline, voice_model, voiceline_location, settings, aggro=0):
        """Synthesize the audio for the character specified using ParlerTTS"""
        logging.output(f'{self.tts_slug} - synthesizing {voiceline} with voice model "{voice_model}"...')
        speaker_wav_path = self.get_speaker_wav_path(voice_model)
        # settings = self.voice_model_settings(voice_model)
        logging.output(f'{self.tts_slug} - using voice model settings: {settings}')
        if not voiceline.endswith(".") and not voiceline.endswith("!") and not voiceline.endswith("?"): # Add a period to the end of the voiceline if it doesn't have one. StyleTTS2 will make a strange blip sound if the voiceline doesn't end with a period.
            voiceline += "."
        self.model.inference(voiceline,
            target_voice_path=speaker_wav_path,
            output_wav_file=voiceline_location,
            alpha=settings.get("alpha", self.default_voice_model_settings["alpha"]),
            beta=settings.get("beta", self.default_voice_model_settings["beta"]),
            diffusion_steps=settings.get("diffusion_steps", self.default_voice_model_settings["diffusion_steps"]),
            embedding_scale=settings.get("embedding_scale", self.default_voice_model_settings["embedding_scale"])
        )
        logging.output(f'{self.tts_slug} - synthesized {voiceline} with voice model "{voice_model}"')