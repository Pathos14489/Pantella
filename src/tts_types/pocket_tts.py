from src.logging import logging
logging.info("Importing pocket_tts.py...")
import random
import src.tts_types.base_tts as base_tts
imported = False
try:
    logging.info("Trying to import pocket_tts")
    from pocket_tts import TTSModel, export_model_state
    from pocket_tts.data.audio import audio_read
    from pocket_tts.data.audio_utils import convert_audio
    import torch
    import io
    import os
    import soundfile as sf
    from scipy.signal import resample
    import scipy.io.wavfile
    imported = True
    logging.info("Imported pocket_tts")
except Exception as e:
    logging.error(f"Failed to import pocket_tts: {e}")
    raise e
logging.info("Imported required libraries in pocket_tts.py")
tts_slug = "pocket_tts"
tts_name = "Pocket-TTS"
default_settings = {
    "pocket_tts_pregen_model_states": True,
    "pocket_tts_banned_voice_models": [],
}
settings_description = {
    "pocket_tts_pregen_model_states": "Whether to pre-cache/pre-generate model states for all available voice models when Pocket-TTS is initialized. This can significantly reduce synthesis times for the first few syntheses for each voice model, at the cost of longer initialization time and higher memory usage when Pocket-TTS is initialized. If you have a lot of voice models and/or limited memory, you may want to set this to false.",
    "pocket_tts_banned_voice_models": "A list of voice models to ban from being used by Pocket-TTS. This can be changed in your [game_id]_config.json. This is useful if you have a voice model that causes issues with Pocket-TTS, such as extremely long synthesis times or crashes."
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
        
        self.model = TTSModel.load_model(config="./data/models/pocket_tts/english.yaml")
        self.model_state_cache = {}

        logging.info(f'{self.tts_slug} speaker wavs folders: {self.speaker_wavs_folders}')
        logging.config(f'{self.tts_slug} - Available voices: {self.voices()}')
        if len(self.voices()) > 0:
            random_voice = random.choice(self.voices())
            self._say("Pocket TTS is ready to go.", random_voice)
        if self.config.pocket_tts_pregen_model_states:
            logging.info(f'{self.tts_slug} - Pre-caching/Pre-generating model states for all available voice models...')
            for voice_model in self.voices():
                self.get_model_state_for_voice_model(voice_model)
        loaded = True

    def voices(self):
        """Return a list of available voices"""
        voices = super().voices()
        for banned_voice in self.config.pocket_tts_banned_voice_models:
            if banned_voice in voices:
                voices.remove(banned_voice)
        return voices
    
    @property
    def default_voice_model_settings(self):
        return {}
    
    def get_speaker_safetensors_path(self, voice_model):
        """Get the path to the safetensors file for the given voice model."""
        return os.path.join(os.path.abspath(f"./data/models/pocket_tts/voice_tensors/"), self.config.game_id, self.language['tts_language_code'], voice_model+".safetensors")

    def get_model_state_for_voice_model(self, voice_model):
        if voice_model not in self.model_state_cache:
            speaker_safetensors_path = self.get_speaker_safetensors_path(voice_model)
            os.makedirs(os.path.dirname(speaker_safetensors_path), exist_ok=True)
            if os.path.exists(speaker_safetensors_path):
                model_state_copy = self.model.get_state_for_audio_prompt(speaker_safetensors_path)
                self.model_state_cache[voice_model] = model_state_copy
                # logging.info(f'{self.tts_slug} - loaded cached model state for voice model "{voice_model}" from path: {speaker_safetensors_path}')
            else:
                speaker_wav_path = self.get_speaker_wav_path(voice_model)
                # logging.info(f'{self.tts_slug} - loading speaker wav for voice model "{voice_model}" from path: {speaker_wav_path}')
                
                audio, sr = sf.read(str(speaker_wav_path), dtype="float32")
                if audio.ndim == 1:
                    audio = torch.from_numpy(audio).unsqueeze(0)
                else:
                    audio = torch.from_numpy(audio.mean(axis=1)).unsqueeze(0)

                audio = convert_audio(audio, from_rate=sr, to_rate=self.model.sample_rate, to_channels=1)

                model_state_copy = self.model.get_state_for_audio_prompt(audio)
                export_model_state(model_state_copy, self.get_speaker_safetensors_path(voice_model))
                self.model_state_cache[voice_model] = model_state_copy
        else:
            model_state_copy = self.model_state_cache[voice_model]
        return model_state_copy

    def _synthesize(self, voiceline, voice_model, voiceline_location, settings, aggro=0):
        """Synthesize the audio for the character specified using ParlerTTS"""
        logging.output(f'{self.tts_slug} - synthesizing {voiceline} with voice model "{voice_model}"...')
        model_state_copy = self.get_model_state_for_voice_model(voice_model)
        logging.output(f'{self.tts_slug} - using voice model settings: {settings}')
        
        audio = self.model.generate_audio(model_state_copy, voiceline)

        logging.info(f'{self.tts_slug} - generated audio for {voiceline} with voice model "{voice_model}" at sample rate {self.model.sample_rate}')
        # Save the generated audio to a temporary file
        # sf.write(voiceline_location, audio, self.model.sample_rate, subtype='PCM_16')
        file_io = io.BytesIO()
        scipy.io.wavfile.write(file_io, self.model.sample_rate, audio.numpy())
        self.convert_to_16bit(file_io, voiceline_location)
        
        if self.model is None:
            raise RuntimeError("TTS model is not loaded.")
        logging.output(f'{self.tts_slug} - synthesized {voiceline} with voice model "{voice_model}"')