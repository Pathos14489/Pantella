from src.logging import logging
logging.info("Importing chat_tts.py...")
import src.tts_types.base_tts as base_tts
try:
    logging.info("Trying to import torch and torchaudio")
    import torch
    import torchaudio
    logging.info("Imported torch and torchaudio")
except Exception as e:
    logging.error(f"Failed to import torch and torchaudio: {e}")
    raise e
try:
    logging.info("Trying to import ChatTTS")
    import ChatTTS
    logging.info("Imported ChatTTS")
except Exception as e:
    logging.error(f"Failed to import ChatTTS: {e}")
    raise e
try:
    logging.info("Trying to import av and AudioResampler")
    import av
    from av.audio.resampler import AudioResampler
    logging.info("Imported av and AudioResampler")
except Exception as e:
    logging.error(f"Failed to import av and AudioResampler: {e}")
    raise e
from pathlib import Path
import numpy as np
import os
import json
import io
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
class Synthesizer(base_tts.base_Synthesizer):
    def __init__(self, conversation_manager, ttses = []):
        super().__init__(conversation_manager)
        self.tts_slug = tts_slug
        self.chat = ChatTTS.Chat()
        self.chat.load(compile=False) # Set to True for better performance
        logging.info(f'ChatTTS speaker wavs folders: {self.speaker_wavs_folders}')
        logging.config(f'ChatTTS - Available voices: {self.voices()}')
        if self.config.ensure_all_voice_samples_have_inference_settings:
            logging.output("Ensuring all voice samples have inference settings...")
            for voice in self.voices():
                self.voice_model_settings(voice)
        if len(self.voices()) > 0:
            random_voice = np.random.choice(self.voices())
            self._say("Chat T T S is ready to go.",random_voice)

    @property
    def speaker_wavs_folders(self):
        if "language" in self.config.__dict__:
            speaker_wavs_folders = [
                os.path.abspath(f".\\data\\voice_samples\\{self.language['tts_language_code']}\\")
            ]
        else:
            speaker_wavs_folders = []
            for language_code in os.listdir(".\\data\\voice_samples\\"):
                if not os.path.isdir(f".\\data\\voice_samples\\{language_code}\\"):
                    continue
                speaker_wavs_folders.append(os.path.abspath(f".\\data\\voice_samples\\{language_code}\\"))
        for addon_slug in self.config.addons:
            addon = self.config.addons[addon_slug]
            if "speakers" in addon["addon_parts"]:
                addon_speaker_wavs_folder = self.config.addons_dir + addon_slug + "\\speakers\\"
                if os.path.exists(addon_speaker_wavs_folder):
                    speaker_wavs_folders.append(addon_speaker_wavs_folder)
                else:
                    logging.error(f'speakers folder not found at: {addon_speaker_wavs_folder}')
        # make all the paths absolute
        speaker_wavs_folders = [os.path.abspath(folder) for folder in speaker_wavs_folders]
        return speaker_wavs_folders
    
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
        voices = []
        for speaker_wavs_folder in self.speaker_wavs_folders:
            for speaker_wav_file in os.listdir(speaker_wavs_folder):
                speaker = speaker_wav_file.split(".")[0]
                if speaker_wav_file.endswith(".wav") and speaker not in voices:
                    voices.append(speaker)
        for banned_voice in self.config.chat_tts_banned_voice_models:
            if banned_voice in voices:
                voices.remove(banned_voice)
        return voices
    
    def get_speaker_wav_path(self, voice_model):
        for speaker_wavs_folder in self.speaker_wavs_folders:
            speaker_wav_path = os.path.join(speaker_wavs_folder, f"{voice_model}.wav")
            if os.path.exists(speaker_wav_path):
                return speaker_wav_path
        return None
    
    def voice_model_settings(self, voice_model):
        # speaker voice model settings are stored in ./data/chat_tts_inference_settings/{tts_language_code}/{voice_model}.json
        settings = {
            "infer_code_prompt": self.config.chat_tts_default_infer_code_prompt,
            "infer_code_temperature": self.config.chat_tts_default_infer_code_temperature,
            "infer_code_repetition_penalty": self.config.chat_tts_default_infer_code_repetition_penalty,
            "refine_text_prompt": self.config.chat_tts_default_refine_text_prompt,
            "refine_text_temperature": self.config.chat_tts_default_refine_text_temperature,
            "refine_text_top_P": self.config.chat_tts_default_refine_text_top_p,
            "refine_text_top_K": self.config.chat_tts_default_refine_text_top_k,
            "refine_text_repetition_penalty": self.config.chat_tts_default_refine_text_repetition_penalty
        }
        voice_model_settings_path = os.path.abspath(f".\\data\\chat_tts_inference_settings\\{self.language['tts_language_code']}\\{voice_model}.json")
        if os.path.exists(voice_model_settings_path):
            with open(voice_model_settings_path, "r") as f:
                voice_model_settings = json.load(f)
            for setting in voice_model_settings:
                settings[setting] = voice_model_settings[setting]
        logging.error(f"Voice model settings not found at: {voice_model_settings_path}")
        if "transcription" not in settings:
            logging.info(f"Default Object:", json.dumps({
                "transcription": "FILL THIS OUT WITH TRANSCRIPT OF THE VOICE SAMPLE. The rest of the settings are defaults, tweak them as needed. DO NOT LEAVE TRANSCRIPT AS THIS, IT WILL NOT WORK. The rest is optional.",
                "infer_code_prompt": self.config.chat_tts_default_infer_code_prompt,
                "infer_code_temperature": self.config.chat_tts_default_infer_code_temperature,
                "infer_code_repetition_penalty": self.config.chat_tts_default_infer_code_repetition_penalty,
                "refine_text_prompt": self.config.chat_tts_default_refine_text_prompt,
                "refine_text_temperature": self.config.chat_tts_default_refine_text_temperature,
                "refine_text_top_P": self.config.chat_tts_default_refine_text_top_p,
                "refine_text_top_K": self.config.chat_tts_default_refine_text_top_k,
                "refine_text_repetition_penalty": self.config.chat_tts_default_refine_text_repetition_penalty
            }, indent=4))
            if not os.path.exists(os.path.dirname(voice_model_settings_path)):
                os.makedirs(os.path.dirname(voice_model_settings_path))
            input("Press enter to continue when you have filled out the voice model settings.")
        if not os.path.exists(voice_model_settings_path):
            logging.error(f"Voice model settings was not found at: {voice_model_settings_path}")
            raise FileNotFoundError()
        with open(voice_model_settings_path, "r") as f:
            voice_model_settings = json.load(f)
        return voice_model_settings
    
    def _synthesize(self, voiceline, voice_model, voiceline_location, aggro=0):
        """Synthesize the audio for the character specified using ChatTTS"""
        logging.output(f'ChatTTS - Loading audio sample and parameters for voiceline synthesis for voice model "{voice_model}"...')
        speaker_wav_path = self.get_speaker_wav_path(voice_model)
        
        voice_model_settings = self.voice_model_settings(voice_model)
        logging.output(f'{self.tts_slug} - using voice model settings: {voice_model_settings}')

        transcription = voice_model_settings["transcription"]
        
        infer_code_prompt = voice_model_settings["infer_code_prompt"]
        infer_code_temperature = voice_model_settings["infer_code_temperature"]
        infer_code_repetition_penalty = voice_model_settings["infer_code_repetition_penalty"]
        
        refine_text_prompt = voice_model_settings["refine_text_prompt"]
        refine_text_temperature = voice_model_settings["refine_text_temperature"]
        refine_text_top_P = voice_model_settings["refine_text_top_P"]
        refine_text_top_K = voice_model_settings["refine_text_top_K"]
        refine_text_repetition_penalty = voice_model_settings["refine_text_repetition_penalty"]
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
