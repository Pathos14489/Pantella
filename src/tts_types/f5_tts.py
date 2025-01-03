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
    logging.info("Imported f5_tts")
except Exception as e:
    logging.error(f"Failed to import f5_tts: {e}")
import random
import os
import json
import tempfile

import soundfile as sf
import torchaudio
from cached_path import cached_path

# load models
vocoder = load_vocoder()

def load_f5tts(ckpt_path=str(cached_path("hf://SWivid/F5-TTS/F5TTS_Base/model_1200000.safetensors"))):
    F5TTS_model_cfg = dict(dim=1024, depth=22, heads=16, ff_mult=2, text_dim=512, conv_layers=4)
    return load_model(DiT, F5TTS_model_cfg, ckpt_path)

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
        self.model = load_f5tts()

        logging.info(f'{self.tts_slug} speaker wavs folders: {self.speaker_wavs_folders}')
        logging.config(f'{self.tts_slug} - Available voices: {self.voices()}')
        if len(self.voices()) > 0:
            random_voice = random.choice(self.voices())
            self._say("F Five Tee Tee Es is ready to go.",random_voice)

    @property
    def speaker_wavs_folders(self):
        if "language" in self.config.__dict__: # If the language is specified in the config, only use the speaker wavs folder for that language
            if self.config.linux_mode:
                speaker_wavs_folders = [
                    os.path.abspath(f"./data/voice_samples/{self.language['tts_language_code']}/")
                ]
            else:
                speaker_wavs_folders = [
                    os.path.abspath(f".\\data\\voice_samples\\{self.language['tts_language_code']}\\")
                ]
        else: # Otherwise, use all the speaker wavs folders
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
        for addon_slug in self.config.addons: # Add the speakers folder from each addon to the list of speaker wavs folders
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
        for banned_voice in self.config.f5_tts_banned_voice_models:
            if banned_voice in voices:
                voices.remove(banned_voice)
        return voices
    
    def voice_model_settings(self, voice_model):
        # speaker voice model settings are stored in ./data/chat_tts_inference_settings/{tts_language_code}/{voice_model}.json
        settings = {
            "transcription": ""
        }
        if self.config.linux_mode:
            voice_model_settings_path = os.path.abspath(f"./data/f5_tts_inference_settings/{self.language['tts_language_code']}/{voice_model}.json")
        else:
            voice_model_settings_path = os.path.abspath(f".\\data\\f5_tts_inference_settings\\{self.language['tts_language_code']}\\{voice_model}.json")
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