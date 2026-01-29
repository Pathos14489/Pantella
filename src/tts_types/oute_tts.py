from src.logging import logging
logging.info("Importing outetts.py...")
import src.tts_types.base_tts as base_tts
imported = False
try:
    logging.info("Trying to import outetts")
    import outetts
    import random
    import os
    imported = True
    logging.info("Imported outetts")
except Exception as e:
    logging.error(f"Failed to import outetts: {e}")
    raise e

logging.info("Imported required libraries in outetts.py")

tts_slug = "oute_tts"
default_settings = {
    "temperature": 0.1,
    "repetition_penalty": 1.1,
}
settings_description = {
    "temperature": "The temperature of the generated audio. Lower values result in more stable and consistent speech, while higher values introduce more variation and expressiveness but may lead to less coherent speech.",
    "repetition_penalty": "The repetition penalty of the generated audio.",
}
options = {}
settings = {}
loaded = False
description = "\"is an experimental text-to-speech model that uses a pure language modeling approach to generate speech\". It requires around 5-6GB of VRAM, and--providing it actually generates a voiceline--sounds worse than StyleTTS and xTTS overall."
class Synthesizer(base_tts.base_Synthesizer):
    def __init__(self, conversation_manager, ttses = []):
        global tts_slug, default_settings, loaded
        super().__init__(conversation_manager)
        self.tts_slug = tts_slug
        self._default_settings = default_settings
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
        loaded = True


    def voices(self):
        """Return a list of available voices"""
        voices = super().voices()
        for banned_voice in self.config.oute_tts_banned_voice_models:
            if banned_voice in voices:
                voices.remove(banned_voice)
        return voices
    
    @property
    def default_voice_model_settings(self):
        return {
            "transcription": "",
            "temperature": self.config.oute_tts_default_temperature,
            "repetition_penalty": self.config.oute_tts_default_repetition_penalty,
        }

    def _synthesize(self, voiceline, voice_model, voiceline_location, settings, aggro=0):
        """Synthesize the audio for the character specified using ParlerTTS"""
        logging.output(f'{self.tts_slug} - synthesizing {voiceline} with voice model "{voice_model}"...')
        speaker_wav_path = self.get_speaker_wav_path(voice_model)
        # settings = self.voice_model_settings(voice_model)
        logging.output(f'{self.tts_slug} - using voice model settings: {settings}')
        if not voiceline.endswith(".") and not voiceline.endswith("!") and not voiceline.endswith("?"): # Add a period to the end of the voiceline if it doesn't have one.
            voiceline += "."
        speaker = self.interface.create_speaker(
            audio_path=speaker_wav_path,
            transcript=settings.get("transcription", self.default_voice_model_settings["transcription"])
        )
        max_length = self.config.oute_tts_max_length
        output = self.interface.generate(
            text=voiceline,
            # Lower temperature values may result in a more stable tone,
            # while higher values can introduce varied and expressive speech
            temperature=settings.get("temperature", self.default_voice_model_settings["temperature"]),
            repetition_penalty=settings.get("repetition_penalty", self.default_voice_model_settings["repetition_penalty"]),
            max_length=max_length,

            # Optional: Use a speaker profile for consistent voice characteristics
            # Without a speaker profile, the model will generate a voice with random characteristics
            speaker=speaker,
        )
        output.save(voiceline_location)
        logging.output(f'{self.tts_slug} - synthesized {voiceline} with voice model "{voice_model}"')