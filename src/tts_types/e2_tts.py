from src.logging import logging
logging.info("Importing e2_tts.py...")
import random
import os
import src.tts_types.base_tts as base_tts
imported = False
try:
    logging.info("Trying to import e2_tts")
    from f5_tts.model import UNetT
    from f5_tts.infer.utils_infer import (
        load_vocoder,
        load_model,
        preprocess_ref_audio_text,
        infer_process,
        remove_silence_for_generated_wav,
    )
    # load models
    vocoder = load_vocoder()
    import tempfile
    import soundfile as sf
    import torchaudio
    from cached_path import cached_path

    def load_e2tts(device):
        E2TTS_model_cfg = dict(dim=1024, depth=24, heads=16, ff_mult=4)
        return load_model(UNetT, E2TTS_model_cfg, (cached_path("hf://SWivid/E2-TTS/E2TTS_Base/model_1200000.safetensors")), device=device)
    imported = True
    logging.info("Imported e2_tts")
except Exception as e:
    logging.error(f"Failed to import e2_tts: {e}")
    raise e

logging.info("Imported required libraries in e2_tts.py")

tts_slug = "e2_tts"
default_settings = {
    "speed": 1.0,
    "cfg_strength": 2.0,
}
settings_description = {
    "speed": "The speed of the generated audio. 1.0 is normal speed, 0.5 is half speed, 2.0 is double speed.",
    "cfg_strength": "The CFG strength of the generated audio. 2.0 is normal CFG strength, 1.0 is low CFG strength, 3.0 is high CFG strength.",
}
options = {}
settings = {}
loaded = False
description = "E2-TTS is a new Unet based TTS that was released alongside F5 TTS. It only requires like 1-1.5GB of VRAM, and sounds as good or better than xTTS for a lot of voices."
class Synthesizer(base_tts.base_Synthesizer):
    def __init__(self, conversation_manager, ttses = []):
        global tts_slug, default_settings, loaded
        super().__init__(conversation_manager)
        self.tts_slug = tts_slug
        self._default_settings = default_settings
        logging.info(f"Initializing {self.tts_slug}...")
        self.model = load_e2tts(self.config.e2_tts_device)

        logging.info(f'{self.tts_slug} speaker wavs folders: {self.speaker_wavs_folders}')
        logging.config(f'{self.tts_slug} - Available voices: {self.voices()}')
        if len(self.voices()) > 0:
            random_voice = random.choice(self.voices())
            self._say("Eee Two Tee Tee Es is ready to go.",random_voice)
        loaded = True

    def voices(self):
        """Return a list of available voices"""
        voices = super().voices()
        for banned_voice in self.config.e2_tts_banned_voice_models:
            if banned_voice in voices:
                voices.remove(banned_voice)
        return voices
    
    @property
    def default_voice_model_settings(self):
        return {
            "transcription": "",
            "speed": self.config.e2_tts_default_speed,
            "cfg_strength": self.config.e2_tts_default_cfg_strength,
        }
    
    def infer(self,
        ref_audio_orig,
        ref_text,
        gen_text,
        output_path,
        remove_silence,
        cross_fade_duration=0.15,
        nfe_step=32,
        speed=1,
        show_info=print,
        cfg_strength=2,
        sway_sampling_coef=-1,
    ):

        if not ref_audio_orig:
            raise ValueError("Please provide reference audio.")

        if not ref_text.strip():
            raise ValueError("Please enter reference text.")

        ref_audio, ref_text = preprocess_ref_audio_text(ref_audio_orig, ref_text, show_info=show_info)

        final_wave, final_sample_rate, combined_spectrogram = infer_process(
            ref_audio,
            ref_text,
            gen_text,
            self.model,
            vocoder,
            cross_fade_duration=cross_fade_duration,
            nfe_step=nfe_step,
            speed=speed,
            show_info=show_info,
            cfg_strength=cfg_strength,
            sway_sampling_coef=sway_sampling_coef
        )

        # Remove silence
        if remove_silence:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as f:
                sf.write(f.name, final_wave, final_sample_rate)
                remove_silence_for_generated_wav(f.name)
                final_wave, _ = torchaudio.load(f.name)
            final_wave = final_wave.squeeze().cpu().numpy() * self.config.e2_tts_volume

        # Save the generated audio
        sf.write(output_path, final_wave, final_sample_rate)

        return output_path

    def _synthesize(self, voiceline, voice_model, voiceline_location, settings, aggro=0):
        """Synthesize the audio for the character specified using ParlerTTS"""
        logging.output(f'{self.tts_slug} - synthesizing {voiceline} with voice model "{voice_model}"...')
        speaker_wav_path = self.get_speaker_wav_path(voice_model)
        # settings = self.voice_model_settings(voice_model)
        logging.output(f'{self.tts_slug} - using voice model settings: {settings}')
        if not voiceline.endswith(".") and not voiceline.endswith("!") and not voiceline.endswith("?"): # Add a period to the end of the voiceline if it doesn't have one.
            voiceline += "."
        self.infer(
            ref_audio_orig=speaker_wav_path,
            ref_text=settings.get("transcription", self.default_voice_model_settings["transcription"]),
            gen_text=voiceline,
            output_path=voiceline_location,
            remove_silence=True,
            cross_fade_duration=0.15,
            nfe_step=32,
            speed=settings.get("speed", self.default_voice_model_settings["speed"]),
            cfg_strength= settings.get("cfg_strength", self.default_voice_model_settings["cfg_strength"]),
            sway_sampling_coef=-1,
        )
        logging.output(f'{self.tts_slug} - synthesized {voiceline} with voice model "{voice_model}"')