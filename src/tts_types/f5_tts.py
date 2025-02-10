from src.logging import logging
logging.info("Importing f5_tts.py...")
import src.tts_types.base_tts as base_tts
try:
    logging.info("Trying to import f5_tts")
    from f5_tts.model import DiT
    from f5_tts.infer.utils_infer import (
        load_vocoder,
        load_model,
        preprocess_ref_audio_text,
        infer_process,
        remove_silence_for_generated_wav,
    )
    vocoder = load_vocoder()
    import random
    import os
    import tempfile

    import soundfile as sf
    import torchaudio
    from cached_path import cached_path
    def load_f5tts(device, ckpt_path=str(cached_path("hf://SWivid/F5-TTS/F5TTS_Base/model_1200000.safetensors"))):
        F5TTS_model_cfg = dict(dim=1024, depth=22, heads=16, ff_mult=2, text_dim=512, conv_layers=4)
        return load_model(DiT, F5TTS_model_cfg, ckpt_path, device=device)
    logging.info("Imported f5_tts")
except Exception as e:
    logging.error(f"Failed to import f5_tts: {e}")
    raise e

# load models


# def load_custom(ckpt_path: str, vocab_path="", model_cfg=None):
#     ckpt_path, vocab_path = ckpt_path.strip(), vocab_path.strip()
#     if ckpt_path.startswith("hf://"):
#         ckpt_path = str(cached_path(ckpt_path))
#     if vocab_path.startswith("hf://"):
#         vocab_path = str(cached_path(vocab_path))
#     if model_cfg is None:
#         model_cfg = dict(dim=1024, depth=22, heads=16, ff_mult=2, text_dim=512, conv_layers=4)
#     return load_model(DiT, model_cfg, ckpt_path, vocab_file=vocab_path)

logging.info("Imported required libraries in f5_tts.py")

tts_slug = "f5_tts"
class Synthesizer(base_tts.base_Synthesizer):
    def __init__(self, conversation_manager, ttses = []):
        super().__init__(conversation_manager)
        self.tts_slug = tts_slug
        logging.info(f"Initializing {self.tts_slug}...")
        self.model = load_f5tts(self.config.f5_tts_device)

        logging.info(f'{self.tts_slug} speaker wavs folders: {self.speaker_wavs_folders}')
        logging.config(f'{self.tts_slug} - Available voices: {self.voices()}')
        if len(self.voices()) > 0:
            random_voice = random.choice(self.voices())
            self._say("F Five Tee Tee Es is ready to go.",random_voice)


    def voices(self):
        """Return a list of available voices"""
        voices = []
        for speaker_wavs_folder in self.speaker_wavs_folders:
            for speaker_wav_file in os.listdir(speaker_wavs_folder):
                speaker = speaker_wav_file.split(".")[0]
                if speaker_wav_file.endswith(".wav") and speaker not in voices:
                    voices.append(speaker)
        for banned_voice in self.config.f5_tts_banned_voice_models:
            if banned_voice in voices:
                voices.remove(banned_voice)
        return voices
    
    def infer(self,
        ref_audio_orig,
        ref_text,
        gen_text,
        output_path,
        remove_silence,
        cross_fade_duration=0.15,
        nfe_step=32,
        speed=1,
        cfg_strength=2,
        sway_sampling_coef=-1,
    ):
        if not ref_audio_orig:
            raise ValueError("Please provide reference audio.")

        if not ref_text.strip():
            raise ValueError("Please enter reference text.")

        ref_audio, ref_text = preprocess_ref_audio_text(ref_audio_orig, ref_text)

        final_wave, final_sample_rate, combined_spectrogram = infer_process(
            ref_audio,
            ref_text,
            gen_text,
            self.model,
            vocoder,
            cross_fade_duration=cross_fade_duration,
            nfe_step=nfe_step,
            speed=speed,
            cfg_strength=cfg_strength,
            sway_sampling_coef=sway_sampling_coef
        )

        # Remove silence
        if remove_silence:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as f:
                sf.write(f.name, final_wave, final_sample_rate)
                remove_silence_for_generated_wav(f.name)
                final_wave, _ = torchaudio.load(f.name)
            final_wave = final_wave.squeeze().cpu().numpy() * self.config.f5_tts_volume

        # Save the generated audio
        sf.write(output_path, final_wave, final_sample_rate)

        return output_path

    def _synthesize(self, voiceline, voice_model, voiceline_location, aggro=0):
        """Synthesize the audio for the character specified using ParlerTTS"""
        logging.output(f'{self.tts_slug} - synthesizing {voiceline} with voice model "{voice_model}"...')
        speaker_wav_path = self.get_speaker_wav_path(voice_model)
        settings = self.voice_model_settings(voice_model)
        logging.output(f'{self.tts_slug} - using voice model settings: {settings}')
        if not voiceline.endswith(".") and not voiceline.endswith("!") and not voiceline.endswith("?"): # Add a period to the end of the voiceline if it doesn't have one.
            voiceline += "."
        self.infer(
            ref_audio_orig=speaker_wav_path,
            ref_text=settings["transcription"],
            gen_text=voiceline,
            output_path=voiceline_location,
            remove_silence=True,
            cross_fade_duration=0.15,
            nfe_step=32,
            speed=1,
            cfg_strength=2,
            sway_sampling_coef=-1,
        )
        logging.output(f'{self.tts_slug} - synthesized {voiceline} with voice model "{voice_model}"')