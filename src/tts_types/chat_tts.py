from src.logging import logging
logging.info("Importing chat_tts.py...")
import src.tts_types.base_tts as base_tts
imported = False
importing_errors = False
try:
    logging.info("Trying to import torch and torchaudio")
    import torch
    import torchaudio
    logging.info("Imported torch and torchaudio")
except Exception as e:
    importing_errors = True
    logging.error(f"Failed to import torch and torchaudio: {e}")
    raise e
try:
    logging.info("Trying to import ChatTTS")
    import ChatTTS
    logging.info("Imported ChatTTS")
except Exception as e:
    importing_errors = True
    logging.error(f"Failed to import ChatTTS: {e}")
    raise e
try:
    logging.info("Trying to import av and AudioResampler")
    import av
    from av.audio.resampler import AudioResampler
    logging.info("Imported av and AudioResampler")
except Exception as e:
    importing_errors = True
    logging.error(f"Failed to import av and AudioResampler: {e}")
    raise e
try:
    logging.info("Trying to import required libraries")
    from pathlib import Path
    import numpy as np
    import random
    import os
    import json
    import io
    logging.info("Imported required libraries")
except Exception as e:
    importing_errors = False
    logging.error(f"Failed to import required libraries: {e}")
    raise e
if not importing_errors:
    imported = True
    
logging.info("Imported required libraries in chat_tts.py")

def format_text(text: str) -> str:
    text = text.replace("\n", " ").replace("\r", " ").replace(".",".[uv_break]").replace("?","?[uv_break]").replace("!","![uv_break]")
    text = text.strip()
    if not text.endswith("[uv_break]"):
        text += "[uv_break]"
    if not text.startswith("[uv_break]"):
        text = "[uv_break]" + text
    text = text.strip()
    return text

tts_slug = "chat_tts"
default_settings = {
    "infer_code_prompt": "[speed_3]",
    "infer_code_temperature": 0.3,
    "infer_code_repetition_penalty": 1.05,
    "refine_text_prompt": "",
    "refine_text_temperature": 0.7,
    "refine_text_top_P": 0.7,
    "refine_text_top_K": 20,
    "refine_text_repetition_penalty": 1.0
}
settings_description = {
    "infer_code_prompt": "The prompt to use for the infer code. Made by combining the following options together: [uv_break],[v_break],[lbreak],[llbreak],[undefine],[laugh],[spk_emb],[empty_spk],[music],[pure],[break_0],[break_1],[break_2],[break_3],[break_4],[break_5],[break_6],[break_7],[laugh_0],[laugh_1],[laugh_2],[oral_0],[oral_1],[oral_2],[oral_3],[oral_4],[oral_5],[oral_6],[oral_7],[oral_8],[oral_9],[speed_0],[speed_1],[speed_2],[speed_3],[speed_4],[speed_5],[speed_6],[speed_7],[speed_8],[speed_9]",
    "infer_code_temperature": "The temperature to use for the infer code. Lower values make the output more deterministic, higher values make it more random.",
    "infer_code_repetition_penalty": "The repetition penalty to use for the infer code. Higher values make the output less repetitive.",
    "refine_text_prompt": "The prompt to use for the refine text. Made by combining the following options together: [uv_break],[v_break],[lbreak],[llbreak],[undefine],[laugh],[spk_emb],[empty_spk],[music],[pure],[break_0],[break_1],[break_2],[break_3],[break_4],[break_5],[break_6],[break_7],[laugh_0],[laugh_1],[laugh_2],[oral_0],[oral_1],[oral_2],[oral_3],[oral_4],[oral_5],[oral_6],[oral_7],[oral_8],[oral_9]",
    "refine_text_temperature": "The temperature to use for the refine text. Lower values make the output more deterministic, higher values make it more random.",
    "refine_text_top_P": "The top P to use for the refine text. Lower values make the output more deterministic, higher values make it more random.",
    "refine_text_top_K": "The top K to use for the refine text. Lower values make the output more deterministic, higher values make it more random.",
    "refine_text_repetition_penalty": "The repetition penalty to use for the refine text. Higher values make the output less repetitive."
}
options = {}
settings = {}
loaded = False
description = "ChatTTS is a relatively new TTS that is fairly unstable in my testing, but sounds really good and has the capability to laugh. I wouldn't really recommend it for casual use, but for playing around it's pretty funny."
class Synthesizer(base_tts.base_Synthesizer):
    def __init__(self, conversation_manager, ttses = []):
        global tts_slug, default_settings, loaded
        super().__init__(conversation_manager)
        self.tts_slug = tts_slug
        self._default_settings = default_settings
        self.chat = ChatTTS.Chat()
        self.chat.load(compile=False) # Set to True for better performance
        logging.info(f'ChatTTS speaker wavs folders: {self.speaker_wavs_folders}')
        logging.config(f'ChatTTS - Available voices: {self.voices()}')
        if self.config.ensure_all_voice_samples_have_inference_settings:
            logging.output("Ensuring all voice samples have inference settings...")
            for voice in self.voices():
                self.voice_model_settings(voice)
        if len(self.voices()) > 0:
            random_voice = random.choice(self.voices())
            self._say("Chat T T S is ready to go.",random_voice)
        loaded = True
    
    @staticmethod
    def load_audio(file: str, sr: int) -> np.ndarray:
        """
        https://github.com/fumiama/Retrieval-based-Voice-Conversion-WebUI/blob/412a9950a1e371a018c381d1bfb8579c4b0de329/infer/lib/audio.py#L39
        """

        if not Path(file).exists():
            raise FileNotFoundError(f"File not found: {file}")

        try:
            container = av.open(file)
            resampler = AudioResampler(format="fltp", layout="mono", rate=sr)

            # Estimated maximum total number of samples to pre-allocate the array
            # AV stores length in microseconds by default
            estimated_total_samples = int(container.duration * sr // 1_000_000)
            decoded_audio = np.zeros(estimated_total_samples + 1, dtype=np.float32)

            offset = 0
            for frame in container.decode(audio=0):
                frame.pts = None  # Clear presentation timestamp to avoid resampling issues
                resampled_frames = resampler.resample(frame)
                for resampled_frame in resampled_frames:
                    frame_data = resampled_frame.to_ndarray()[0]
                    end_index = offset + len(frame_data)

                    # Check if decoded_audio has enough space, and resize if necessary
                    if end_index > decoded_audio.shape[0]:
                        decoded_audio = np.resize(decoded_audio, end_index + 1)

                    decoded_audio[offset:end_index] = frame_data
                    offset += len(frame_data)

            # Truncate the array to the actual size
            decoded_audio = decoded_audio[:offset]
        except Exception as e:
            raise RuntimeError(f"Failed to load audio: {e}")

        return decoded_audio

    def voices(self):
        """Return a list of available voices"""
        voices = super().voices()
        for banned_voice in self.config.chat_tts_banned_voice_models:
            if banned_voice in voices:
                voices.remove(banned_voice)
        return voices
 
    @property
    def default_voice_model_settings(self):
        return {
            "transcription": "FILL THIS OUT WITH TRANSCRIPT OF THE VOICE SAMPLE. The rest of the settings are defaults, tweak them as needed. DO NOT LEAVE TRANSCRIPT AS THIS, IT WILL NOT WORK. The rest is optional.",
            "infer_code_prompt": self.config.chat_tts_default_infer_code_prompt,
            "infer_code_temperature": self.config.chat_tts_default_infer_code_temperature,
            "infer_code_repetition_penalty": self.config.chat_tts_default_infer_code_repetition_penalty,
            "refine_text_prompt": self.config.chat_tts_default_refine_text_prompt,
            "refine_text_temperature": self.config.chat_tts_default_refine_text_temperature,
            "refine_text_top_P": self.config.chat_tts_default_refine_text_top_p,
            "refine_text_top_K": self.config.chat_tts_default_refine_text_top_k,
            "refine_text_repetition_penalty": self.config.chat_tts_default_refine_text_repetition_penalty
        }
    
    def _synthesize(self, voiceline, voice_model, voiceline_location, settings, aggro=0):
        """Synthesize the audio for the character specified using ChatTTS"""
        logging.output(f'ChatTTS - Loading audio sample and parameters for voiceline synthesis for voice model "{voice_model}"...')
        speaker_wav_path = self.get_speaker_wav_path(voice_model)
        
        logging.output(f'{self.tts_slug} - using voice model settings: {settings}')

        transcription = settings.get("transcription", self.default_voice_model_settings["transcription"])
        
        infer_code_prompt = settings.get("infer_code_prompt", self.default_voice_model_settings["infer_code_prompt"])
        infer_code_temperature = settings.get("infer_code_temperature", self.default_voice_model_settings["infer_code_temperature"])
        infer_code_repetition_penalty = settings.get("infer_code_repetition_penalty", self.default_voice_model_settings["infer_code_repetition_penalty"])
        
        refine_text_prompt = settings.get("refine_text_prompt", self.default_voice_model_settings["refine_text_prompt"])
        refine_text_temperature = settings.get("refine_text_temperature", self.default_voice_model_settings["refine_text_temperature"])
        refine_text_top_P = settings.get("refine_text_top_P", self.default_voice_model_settings["refine_text_top_P"])
        refine_text_top_K = settings.get("refine_text_top_K", self.default_voice_model_settings["refine_text_top_K"])
        refine_text_repetition_penalty = settings.get("refine_text_repetition_penalty", self.default_voice_model_settings["refine_text_repetition_penalty"])
        logging.output("Loading audio...")
        # np.ndarray wav
        wav = self.load_audio(speaker_wav_path,24000)
        
        logging.output("Sampling speaker...")
        speaker_sample = self.chat.sample_audio_speaker(wav)
        logging.output("Speaker sampled")
        logging.output("Getting infer_code params...")
        speaker_params_infer_code = ChatTTS.Chat.InferCodeParams(
            spk_smp=speaker_sample,
            txt_smp=transcription,# "test", # not sure if this is correct?
            prompt=infer_code_prompt,
            temperature=infer_code_temperature,
            repetition_penalty=infer_code_repetition_penalty
        )

        logging.output("Getting refine_text params...")
        params_refine_text = ChatTTS.Chat.RefineTextParams(
            prompt=refine_text_prompt,
            temperature=refine_text_temperature,
            top_P=refine_text_top_P,
            top_K=refine_text_top_K,
            repetition_penalty=refine_text_repetition_penalty,
        )
        voiceline = format_text(voiceline)
        logging.output(f"ChatTTS - generating voiceline: {voiceline}")
        wavs = self.chat.infer([voiceline],
            params_infer_code=speaker_params_infer_code,
            params_refine_text=params_refine_text
        )
        logging.output("ChatTTS - Voiceline synthesized, saving to disk...")
        file_bytes = io.BytesIO()
        torchaudio.save(file_bytes, torch.from_numpy(wavs[0]).unsqueeze(0), 24000, format="wav")
        file_bytes.seek(0)
        # open temp_voiceline_location with io.BytesIO
        # convert to 16 bit
        self.convert_to_16bit(file_bytes,output_file=voiceline_location)
        if not os.path.exists(voiceline_location):
            logging.error(f'ChatTTS failed to generate voiceline at: {Path(voiceline_location)}')
            raise FileNotFoundError()
