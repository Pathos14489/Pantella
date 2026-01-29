from src.logging import logging
logging.info("Importing parler_tts.py...")
import src.tts_types.base_tts as base_tts
imported = False
importing_errors = False
try:
    logging.info("Trying to import torch")
    import torch
    logging.info("Imported torch and torchaudio")
except Exception as e:
    logging.error(f"Failed to import torch and torchaudio: {e}")
    importing_errors = True
    raise e
try:
    logging.info("Trying to import ParlerTTS")
    from parler_tts import ParlerTTSForConditionalGeneration
    logging.info("Imported ParlerTTS")
except Exception as e:
    logging.error(f"Failed to import ParlerTTS: {e}")
    importing_errors = True
    raise e
try:
    logging.info("Trying to import Tokenizer from transformers")
    from transformers import AutoTokenizer
    logging.info("Imported Tokenizer from transformers")
except Exception as e:
    logging.error(f"Failed to import av and AudioResampler: {e}")
    importing_errors = True
    raise e
try:
    import os
    import json
    import random
    import soundfile as sf
except Exception as e:
    logging.error(f"Failed to import os, json, random, and soundfile: {e}")
    importing_errors = True
    raise e
if not importing_errors:
    imported = True
logging.info("Imported required libraries in parler_tts.py")

tts_slug = "parler_tts"
default_settings = {
    "temperature": 1.0,
}
settings_description = {
    "temperature": "The temperature of the generated audio. Lower values result in more stable and consistent speech, while higher values introduce more variation and expressiveness but may lead to less coherent speech.",
}
options = {}
settings = {}
loaded = False
description = "ParlerTTS is a TTS from Huggingface. It's a bit of a stange one, this TTS doesn't require a voice sample to make a new voice, it requires a text description of the voice you want it to sound like. Including stuff like \"Noisy audio\" \"Clear audio\", etc. So Example: \"A voice that sounds like a young woman with a clear voice and a slight accent\". It's a bit of a strange one, but I could see it being useful if someone wanted to add and customize the voice for a custom NPC without having to go find a clear good quality voice sample of the voice they want to use."
class Synthesizer(base_tts.base_Synthesizer):
    def __init__(self, conversation_manager, ttses = []):
        global tts_slug, default_settings, loaded
        super().__init__(conversation_manager)
        self.tts_slug = tts_slug
        self._default_settings = default_settings
        logging.info(f"Initializing {self.tts_slug}({self.config.parler_tts_model}) to device {self.config.parler_tts_device}")
        self.model = ParlerTTSForConditionalGeneration.from_pretrained(self.config.parler_tts_model).to(self.config.parler_tts_device)
        self.tokenizer = AutoTokenizer.from_pretrained(self.config.parler_tts_model)
        
        if self.config.parler_tts_compile:
            logging.info(f'Compiling {self.tts_slug} model...')
            self.model.generation_config.cache_implementation = "static"
            self.model.forward = torch.compile(self.model.forward, mode=self.config.parler_tts_compile_mode)
            logging.info(f'{self.tts_slug} model compiled successfully')

            inputs = self.tokenizer("This is for compilation", return_tensors="pt", padding="max_length", max_length=self.config.parler_tts_max_length).to(self.config.parler_tts_device)
            model_kwargs = {**inputs, "prompt_input_ids": inputs.input_ids, "prompt_attention_mask": inputs.attention_mask, }

            logging.info(f'Warming up {self.tts_slug} model...')
            n_steps = 1 if self.config.parler_tts_compile_mode == "script" else 2
            for _ in range(n_steps):
                _ = self.model.generate(**model_kwargs)
            logging.info(f'{self.tts_slug} model warmed up successfully')

        self._voices = None
        logging.info(f'{self.tts_slug} speaker settings folders: {self.voice_settings_folders}')
        logging.config(f'{self.tts_slug} - Available voices: {self.voices()}')
        if len(self.voices()) > 0:
            random_voice = random.choice(self.voices())
            self._say("Parler is ready to go.",random_voice)
        loaded = True

    def voices(self):
        """Return a list of available voices"""
        if self._voices == None:
            voices = []
            for speaker_wavs_folder in self.voice_settings_folders:
                for file in os.listdir(speaker_wavs_folder):
                    if file.endswith(".json"):
                        with open(os.path.join(speaker_wavs_folder, file), 'r', encoding="utf8") as f:
                            json_data = json.load(f)
                            json_data['voice_model'] = file.replace(".json", "")
                            voices.append(json_data)
            self._voices = voices
        for banned_voice in self.config.parler_banned_voice_models:
            if banned_voice in self._voices:
                self._voices.remove(banned_voice)
        return [voice["voice_model"] for voice in self._voices]
    
    @property
    def default_voice_model_settings(self):
        return {
            "description": "",
            "temperature": self.config.parler_tts_defaulit_temperature,
        }
    
    def _synthesize(self, voiceline, voice_model, voiceline_location, settings, aggro=0):
        """Synthesize the audio for the character specified using ParlerTTS"""
        logging.output(f'{self.tts_slug} - Loading voice model settings for {voice_model}')
        # voice_model_settings = self.voice_model_settings(voice_model)
        input_ids = self.tokenizer(settings['description'], return_tensors="pt").input_ids.to(self.config.parler_tts_device)
        voiceline_input_ids = self.tokenizer(voiceline, return_tensors="pt").input_ids.to(self.config.parler_tts_device)

        generation = self.model.generate(
            input_ids=input_ids,
            prompt_input_ids=voiceline_input_ids,
            temperature = settings.get("temperature", self.default_voice_model_settings["temperature"]),
        )
        audio_arr = generation.cpu().numpy().squeeze()
        sf.write(voiceline_location, audio_arr, self.model.config.sampling_rate)
