import src.utils as utils
import src.tts_types.base_tts as base_tts
from src.logging import logging
import sys
import os
from pathlib import Path
import requests
import io
import soundfile as sf
import numpy as np
import os
import torch
import torchaudio
from TTS.tts.configs.xtts_config import XttsConfig
from TTS.tts.models.xtts import Xtts

tts_slug = "xtts"
class Synthesizer(base_tts.base_Synthesizer): 
    def __init__(self, conversation_manager):
        super().__init__(conversation_manager)
        
        xtts_config = XttsConfig()
        xtts_config.load_json(".\\data\\models\\xtts\\config.json")
        self.model = Xtts.init_from_config(xtts_config)
        self.model.load_checkpoint(xtts_config, checkpoint_dir=".\\data\\models\\xtts", use_deepspeed=True)
        self.model.to(self.config.xtts_device)
            
        self.latent_cache = {}
        if self.config.xtts_preload_latents:
            self.preload_latents()

        logging.info(f'xTTS - Available voices: {self.voices()}')

    def preload_latents(self):
        """Preload latents for all voice models"""
        for voice in self.voices():
            self.get_latent(voice)

    def get_latent(self, voice):
        """Get latent for voice model"""
        if voice in self.latent_cache and self.config.xtts_use_cached_latents:
            logging.info(f'xTTS - Using cached latent for voice: {voice}')
            return self.latent_cache[voice]
        logging.info(f'xTTS - Generating latent for voice: {voice}')
        gpt_cond_latent, speaker_embedding = self.model.get_conditioning_latents(audio_path=[f"{self.config.xtts_voice_samples_dir}\\{voice}.wav"])
        self.latent_cache[voice] = (gpt_cond_latent, speaker_embedding)
        return gpt_cond_latent, speaker_embedding

    def voices(self):
        """Return a list of available voices"""
        absolute_path = Path(os.getcwd(), self.config.xtts_voice_samples_dir)
        voice_samples = os.listdir(absolute_path)
        voices = [voice_sample.split('.')[0] for voice_sample in voice_samples]
        voices = [voice for voice in voices if voice != '']
        return voices
    
    def synthesize(self, voiceline, character, **kwargs):
        """Synthesize the text for the character specified using either the 'tts_override' property of the character or using the first tts engine that supports the voice model of the character"""
        logging.info(f'Synthesizing voiceline: {voiceline}')
        # make voice model folder if it doesn't already exist
        if not os.path.exists(f"{self.output_path}/voicelines/{character.voice_model}"):
            os.makedirs(f"{self.output_path}/voicelines/{character.voice_model}")

        final_voiceline_file =  f"{self.output_path}/voicelines/{character.voice_model}/voiceline.wav"
        
        gpt_cond_latent, speaker_embedding = self.get_latent(character.voice_model)

        out = self.model.inference(
            voiceline,
            character.language_code,
            gpt_cond_latent,
            speaker_embedding,
            temperature=self.config.xtts_temperature,
            length_penalty=self.config.xtts_length_penalty,
            repetition_penalty=self.config.xtts_repetition_penalty,
            top_k=self.config.xtts_top_k,
            top_p=self.config.xtts_top_p,
            num_beams=self.config.xtts_num_beams,
            speed=self.config.xtts_speed,
            enable_text_splitting=True
        )
        torchaudio.save(final_voiceline_file, torch.tensor(out["wav"]).unsqueeze(0), 24000)
        
        if not os.path.exists(final_voiceline_file):
            logging.error(f'xTTS failed to generate voiceline at: {Path(final_voiceline_file)}')
            raise FileNotFoundError()

        self.lip_gen(voiceline, final_voiceline_file)
        self.debug(final_voiceline_file)

        return final_voiceline_file
    