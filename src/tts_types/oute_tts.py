from src.logging import logging
logging.info("Importing outetts.py...")
import src.tts_types.base_tts as base_tts
try:
    logging.info("Trying to import outetts")
    import outetts
    import random
    import os
    logging.info("Imported outetts")
except Exception as e:
    logging.error(f"Failed to import outetts: {e}")
    raise e

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
    
    @property
    def default_voice_model_settings(self):
        return {
            "transcription": "",
            "temperature": 0.1,
            "repetition_penalty": 1.1,
        }
    

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