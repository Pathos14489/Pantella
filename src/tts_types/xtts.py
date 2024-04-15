print("Loading xtts.py")
from src.logging import logging
import src.tts_types.base_tts as base_tts
# from pathlib import Path
# import os
# import torch
# F = torch.nn.functional
# import soundfile as sf
# import numpy as np
# from TTS.tts.configs.xtts_config import XttsConfig
# from TTS.tts.models.xtts import Xtts
# from TTS.tts.layers.xtts.tokenizer import split_sentence
logging.info("Imported required libraries in xtts.py")

# class Patched_xTTS(Xtts):
#     def __init__(self, config):
#         super().__init__(config)
        
#     @torch.inference_mode()
#     def inference(
#         self,
#         text,
#         language,
#         gpt_cond_latent,
#         speaker_embedding,
#         # GPT inference
#         temperature=0.75,
#         length_penalty=1.0,
#         repetition_penalty=10.0,
#         top_k=50,
#         top_p=0.85,
#         do_sample=True,
#         num_beams=1,
#         speed=1.0,
#         enable_text_splitting=False,
#         **hf_generate_kwargs,
#     ):
#         language = language.split("-")[0]  # remove the country code
#         length_scale = 1.0 / max(speed, 0.05)
#         if enable_text_splitting:
#             text = split_sentence(text, language, self.tokenizer.char_limits[language])
#         else:
#             text = [text]

#         wavs = []
#         gpt_latents_list = []
#         for sent in text:
#             sent = sent.strip().lower()
#             text_tokens = torch.IntTensor(self.tokenizer.encode(sent, lang=language)).unsqueeze(0).to(self.device)

#             assert (
#                 text_tokens.shape[-1] < self.args.gpt_max_text_tokens
#             ), " ❗ XTTS can only generate text with a maximum of 400 tokens."

#             with torch.no_grad():
#                 gpt_cond_latent = gpt_cond_latent.to(self.device)
#                 speaker_embedding = speaker_embedding.to(self.device)
#                 gpt_codes = self.gpt.generate(
#                     cond_latents=gpt_cond_latent,
#                     text_inputs=text_tokens,
#                     input_tokens=None,
#                     do_sample=do_sample,
#                     top_p=top_p,
#                     top_k=top_k,
#                     temperature=temperature,
#                     num_return_sequences=self.gpt_batch_size,
#                     num_beams=num_beams,
#                     length_penalty=length_penalty,
#                     repetition_penalty=repetition_penalty,
#                     output_attentions=False,
#                     **hf_generate_kwargs,
#                 )
#                 expected_output_len = torch.tensor(
#                     [gpt_codes.shape[-1] * self.gpt.code_stride_len], device=text_tokens.device
#                 )

#                 text_len = torch.tensor([text_tokens.shape[-1]], device=self.device)
#                 gpt_latents = self.gpt(
#                     text_tokens,
#                     text_len,
#                     gpt_codes,
#                     expected_output_len,
#                     cond_latents=gpt_cond_latent,
#                     return_attentions=False,
#                     return_latent=True,
#                 )

#                 if length_scale != 1.0:
#                     gpt_latents = F.interpolate(
#                         gpt_latents.transpose(1, 2), scale_factor=length_scale, mode="linear"
#                     ).transpose(1, 2)

#                 gpt_latents_list.append(gpt_latents.cpu())
#                 wavs.append(self.hifigan_decoder(gpt_latents, g=speaker_embedding).cpu().squeeze())

#         return {
#             "wav": torch.cat(wavs, dim=0).numpy(),
#             "gpt_latents": torch.cat(gpt_latents_list, dim=1).numpy(),
#             "speaker_embedding": speaker_embedding,
#         }

tts_slug = "xtts"
class Synthesizer(base_tts.base_Synthesizer): 
    def __init__(self, conversation_manager):
        super().__init__(conversation_manager)
        
    #     xtts_config = XttsConfig()
    #     xtts_config.load_json(".\\data\\models\\xtts\\config.json")
    #     self.model = Patched_xTTS.init_from_config(xtts_config)
    #     self.model.load_checkpoint(xtts_config, checkpoint_dir=".\\data\\models\\xtts", use_deepspeed=True)
    #     self.model.to(self.config.xtts_device)
    #     self.model.gpt.to(self.config.xtts_device)
    #     self.model.hifigan_decoder.to(self.config.xtts_device)
            
    #     self.latent_cache = {}
    #     if self.config.xtts_preload_latents:
    #         self.preload_latents()

    #     logging.info(f'xTTS - Available voices: {self.voices()}')

    # def preload_latents(self):
    #     """Preload latents for all voice models"""
    #     for voice in self.voices():
    #         self.get_latent(voice)

    # def get_latent(self, voice):
    #     """Get latent for voice model"""
    #     voice = voice.replace(" ", "")
    #     if voice in self.latent_cache and self.config.xtts_use_cached_latents:
    #         logging.info(f'xTTS - Using cached latent for voice: {voice}')
    #         return self.latent_cache[voice]
    #     logging.info(f'xTTS - Generating latent for voice: {voice}')
    #     gpt_cond_latent, speaker_embedding = self.model.get_conditioning_latents(audio_path=[Path(os.getcwd(),self.config.xtts_voice_samples_dir,f"{voice}.wav")])
    #     self.latent_cache[voice] = (gpt_cond_latent, speaker_embedding)
    #     return gpt_cond_latent, speaker_embedding

    # def voices(self):
    #     """Return a list of available voices"""
    #     absolute_path = Path(os.getcwd(), self.config.xtts_voice_samples_dir)
    #     voice_samples = os.listdir(absolute_path)
    #     voices = [voice_sample.split('.')[0] for voice_sample in voice_samples]
    #     voices = [voice for voice in voices if voice != '']
    #     return voices
    
    # def synthesize(self, voiceline, character, **kwargs):
    #     """Synthesize the text for the character specified using either the 'tts_override' property of the character or using the first tts engine that supports the voice model of the character"""
    #     logging.info(f'Synthesizing voiceline: {voiceline}')
    #     # make voice model folder if it doesn't already exist
    #     if not os.path.exists(f"{self.output_path}/voicelines/{character.voice_model}"):
    #         os.makedirs(f"{self.output_path}/voicelines/{character.voice_model}")

    #     final_voiceline_file =  f"{self.output_path}/voicelines/{character.voice_model}/voiceline.wav"
        
    #     gpt_cond_latent, speaker_embedding = self.get_latent(character.voice_model)

    #     out = self.model.inference(
    #         voiceline,
    #         character.language_code,
    #         gpt_cond_latent,
    #         speaker_embedding,
    #         temperature=self.config.xtts_temperature,
    #         length_penalty=self.config.xtts_length_penalty,
    #         repetition_penalty=self.config.xtts_repetition_penalty,
    #         top_k=self.config.xtts_top_k,
    #         top_p=self.config.xtts_top_p,
    #         num_beams=self.config.xtts_num_beams,
    #         speed=self.config.xtts_speed,
    #         enable_text_splitting=True
    #     )

    #     if "wav" in out:
    #         data = out["wav"]
    #         # Directly convert to 16-bit if data is in float format and assumed to be in the -1.0 to 1.0 range
    #         if np.issubdtype(data.dtype, np.floating):
    #             # Ensure no value exceeds the -1.0 to 1.0 range before conversion (optional, based on your data's characteristics)
    #             # data = np.clip(data, -1.0, 1.0)  # Uncomment if needed
    #             data_16bit = np.int16(data * 32767)
    #         elif not np.issubdtype(data.dtype, np.int16):
    #             # If data is not floating-point or int16, consider logging or handling this case explicitly
    #             # For simplicity, this example just converts to int16 without scaling
    #             data_16bit = data.astype(np.int16)
    #         else:
    #             # If data is already int16, no conversion is necessary
    #             data_16bit = data

    #         # Write the 16-bit audio data back to a file
    #         sf.write(final_voiceline_file, data_16bit, 24000, subtype='PCM_16')
        
    #     if not os.path.exists(final_voiceline_file):
    #         logging.error(f'xTTS failed to generate voiceline at: {Path(final_voiceline_file)}')
    #         raise FileNotFoundError()

    #     self.lip_gen(voiceline, final_voiceline_file)
    #     self.debug(final_voiceline_file)

    #     return final_voiceline_file
    