print('Loading kyutai_stt.py...')
from src.logging import logging
try:
    logging.info('Importing requirements for kyutai_stt.py...')
    import torch
    import torch._dynamo
    torch._dynamo.config.suppress_errors = True # makes it work even if triton is having issues
    import pyaudio
    import julius
    import moshi.models
    import speech_recognition as sr
    import numpy as np
    import dataclasses
    import itertools
    import math
    import time
except ImportError:
    logging.error('Could not import requirements in kyutai_stt.py. Please ensure the requirements are installed and try again.')
    raise ImportError('Could not import requirements in kyutai_stt.py. Please ensure the requirements are installed and try again.')
from src.stt_types.base_stt import base_Transcriber
logging.info('Imported required libraries in kyutai_stt.py')

@dataclasses.dataclass
class TimestampedText:
    text: str
    timestamp: tuple[float, float]

    def __str__(self):
        return f"{self.text} ({self.timestamp[0]:.2f}:{self.timestamp[1]:.2f})"


def tokens_to_timestamped_text(
    text_tokens,
    tokenizer,
    frame_rate,
    end_of_padding_id,
    padding_token_id,
    offset_seconds,
) -> list[TimestampedText]:
    text_tokens = text_tokens.cpu().view(-1)

    # Normally `end_of_padding` tokens indicate word boundaries.
    # Everything between them should be a single word;
    # the time offset of the those tokens correspond to word start and
    # end timestamps (minus silence prefix and audio delay).
    #
    # However, in rare cases some complexities could arise. Firstly,
    # for words that are said quickly but are represented with
    # multiple tokens, the boundary might be omitted. Secondly,
    # for the very last word the end boundary might not happen.
    # Below is a code snippet that handles those situations a bit
    # more carefully.

    sequence_timestamps = []

    def _tstmp(start_position, end_position):
        return (
            max(0, start_position / frame_rate - offset_seconds),
            max(0, end_position / frame_rate - offset_seconds),
        )

    def _decode(t):
        t = t[t > padding_token_id]
        return tokenizer.decode(t.numpy().tolist())

    def _decode_segment(start, end):
        nonlocal text_tokens
        nonlocal sequence_timestamps

        text = _decode(text_tokens[start:end])
        words_inside_segment = text.split()

        if len(words_inside_segment) == 0:
            return
        if len(words_inside_segment) == 1:
            # Single word within the boundaries, the general case
            sequence_timestamps.append(
                TimestampedText(text=text, timestamp=_tstmp(start, end))
            )
        else:
            # We're in a rare situation where multiple words are so close they are not separated by `end_of_padding`.
            # We tokenize words one-by-one; each word is assigned with as many frames as much tokens it has.
            for adjacent_word in words_inside_segment[:-1]:
                n_tokens = len(tokenizer.encode(adjacent_word))
                sequence_timestamps.append(
                    TimestampedText(
                        text=adjacent_word, timestamp=_tstmp(start, start + n_tokens)
                    )
                )
                start += n_tokens

            # The last word takes everything until the boundary
            adjacent_word = words_inside_segment[-1]
            sequence_timestamps.append(
                TimestampedText(text=adjacent_word, timestamp=_tstmp(start, end))
            )

    (segment_boundaries,) = torch.where(text_tokens == end_of_padding_id)

    if not segment_boundaries.numel():
        return []

    for i in range(len(segment_boundaries) - 1):
        segment_start = int(segment_boundaries[i]) + 1
        segment_end = int(segment_boundaries[i + 1])

        _decode_segment(segment_start, segment_end)

    last_segment_start = int(segment_boundaries[-1]) + 1

    boundary_token = torch.tensor([tokenizer.eos_id()])
    (end_of_last_segment,) = torch.where(
        torch.isin(text_tokens[last_segment_start:], boundary_token)
    )

    if not end_of_last_segment.numel():
        # upper-bound either end of the audio or 1 second duration, whichever is smaller
        last_segment_end = min(text_tokens.shape[-1], last_segment_start + frame_rate)
    else:
        last_segment_end = last_segment_start + int(end_of_last_segment[0].item())
    _decode_segment(int(last_segment_start), int(last_segment_end))

    return sequence_timestamps


stt_slug = "kyutai_stt"

class Transcriber(base_Transcriber):
    def __init__(self, game_interface):
        global stt_slug
        super().__init__(game_interface)
        self.stt_slug = stt_slug
        self.args = {
            "hf_repo": "kyutai/stt-1b-en_fr-candle",
            "moshi_weight": None,
            "mimi_weight": None,
            "tokenizer": None,
            "config_path": None,
            "device": "cuda",
            "vad": True,
        }
        
        self.info = moshi.models.loaders.CheckpointInfo.from_hf_repo(
            self.args["hf_repo"],
            moshi_weights=self.args["moshi_weight"],
            mimi_weights=self.args["mimi_weight"],
            tokenizer=self.args["tokenizer"],
            config_path=self.args["config_path"],
        )

        self.mimi = self.info.get_mimi(device=self.args["device"])
        self.tokenizer = self.info.get_text_tokenizer()
        self.lm = self.info.get_moshi(
            device=self.args["device"],
            dtype=torch.bfloat16,
        )
        self.lm_gen = moshi.models.LMGen(self.lm, temp=0, temp_text=0.0)
        
        self.FORMAT = pyaudio.paInt16
        self.CHANNELS = 1
        self.SAMPLE_RATE = 16000
        self.CHUNK = int(self.SAMPLE_RATE / 10)

    def initialize(self):
        # self.speech_processor = create_Speech_Input_Processor(self)
        self.initialized = True

    # Provided by Alexander Veysov to silero_vad repo
    def int2float(self, sound):
        abs_max = np.abs(sound).max()
        sound = sound.astype('float32')
        if abs_max > 0:
            sound *= 1/32768
        sound = sound.squeeze()  # depends on the use case
        return sound
    
    def recognize_input(self, possible_names_list):
        """
        Recognize input from mic and return transcript if activation tag (assistant name) exist
        """
        
        # audio, input_sample_rate = sphn.read(audio_file)
        # audio = torch.from_numpy(audio).to(self.args["device"])
        # audio = julius.resample_frac(audio, input_sample_rate, self.mimi.sample_rate)
        # if audio.shape[-1] % self.mimi.frame_size != 0:
        #     to_pad = self.mimi.frame_size - audio.shape[-1] % self.mimi.frame_size
        #     audio = torch.nn.functional.pad(audio, (0, to_pad))
        
        done_speaking = False
        data = bytearray()
        def mic_generator():
            audio = pyaudio.PyAudio()
            num_samples = 1280
            stream = audio.open(format=self.FORMAT,
                channels=self.CHANNELS,
                rate=self.SAMPLE_RATE,
                input=True,
                frames_per_buffer=self.CHUNK,
            )

            print("Started Recording")
            while not done_speaking:
                raw_audio_chunk = stream.read(num_samples, exception_on_overflow = False)
                if raw_audio_chunk:
                    audio_chunk = np.frombuffer(raw_audio_chunk, np.int16)
                    audio_chunk = self.int2float(audio_chunk)
                    audio_chunk = torch.from_numpy(audio_chunk).to(self.args["device"])
                    audio_chunk = julius.resample_frac(audio_chunk, self.SAMPLE_RATE, self.mimi.sample_rate)
                    if audio_chunk.shape[-1] % self.mimi.frame_size != 0:
                        to_pad = self.mimi.frame_size - audio_chunk.shape[-1] % self.mimi.frame_size
                        print(f"Padding audio chunk with {to_pad} zeros")
                        audio_chunk = torch.nn.functional.pad(audio_chunk, (0, to_pad))
                    audio_chunk = audio_chunk.view(1, 1, -1)
                    yield audio_chunk
            stream.stop_stream()
            stream.close()
            audio.terminate()
            print("Stopped the recording")


        audio_silence_prefix_seconds = self.info.stt_config.get(
            "audio_silence_prefix_seconds", 1.0
        )
        audio_delay_seconds = self.info.stt_config.get("audio_delay_seconds", 5.0)
        padding_token_id = self.info.raw_config.get("text_padding_token_id", 3)


        text_tokens_accum = []

        n_prefix_chunks = math.ceil(audio_silence_prefix_seconds * self.mimi.frame_rate)
        n_suffix_chunks = math.ceil(audio_delay_seconds * self.mimi.frame_rate)
        silence_chunk = torch.zeros(
            (1, 1, self.mimi.frame_size), dtype=torch.float32, device=self.args["device"]
        )

        chunks = itertools.chain(
            itertools.repeat(silence_chunk, n_prefix_chunks),
            # torch.split(audio[:, None], self.mimi.frame_size, dim=-1),
            mic_generator(),
            itertools.repeat(silence_chunk, n_suffix_chunks),
        )
        start_time = time.time()
        nchunks = 0
        last_print_was_vad = False
        has_spoken = False
        empty_buffer_count = 4
        empty_buffer = []
        with self.mimi.streaming(1), self.lm_gen.streaming(1):
            for audio_chunk in chunks: # tqdm()
                # print(audio_chunk.shape, audio_chunk.dtype, audio_chunk)
                nchunks += 1
                audio_tokens = self.mimi.encode(audio_chunk)
                # skip if every token is 0
                if torch.all(audio_tokens == 0):
                    continue
                # print(nchunks, audio_tokens)
                # print(nchunks, audio_tokens)
                if self.args['vad']:
                    text_tokens, vad_heads = self.lm_gen.step_with_extra_heads(audio_tokens)
                else:
                    text_tokens = self.lm_gen.step(audio_tokens)
                    vad_heads = None
                text_token = text_tokens[0, 0, 0].cpu().item()
                audio_chunk_bytes = (audio_chunk.squeeze().cpu().numpy() * 32768).astype(np.int16).tobytes()
                if text_token not in (0, 3):
                    if not has_spoken:
                        for chunk in empty_buffer:
                            data.extend(chunk)
                        empty_buffer = []
                        print("User started speaking:")
                    has_spoken = True
                    _text = self.tokenizer.id_to_piece(text_tokens[0, 0, 0].cpu().item())  # type: ignore
                    _text = _text.replace("▁", " ")
                    print(_text, end="", flush=True)
                    last_print_was_vad = False
                    data.extend(audio_chunk_bytes)
                elif not has_spoken:
                    empty_buffer.append(audio_chunk_bytes)
                    if len(empty_buffer) > empty_buffer_count:
                        empty_buffer.pop(0) 
                if vad_heads:
                    pr_vad = vad_heads[2][0, 0, 0].cpu().item()
                    if pr_vad > 0.5 and not last_print_was_vad and has_spoken:
                        print("[end of turn detected:"+f"{pr_vad:.2f}]")
                        done_speaking = True
                        last_print_was_vad = True
                text_tokens_accum.append(text_tokens)

        utterance_tokens = torch.concat(text_tokens_accum, dim=-1)
        dt = time.time() - start_time
        print(
            f"\nprocessed {nchunks} chunks in {dt:.2f} seconds, steps per second: {nchunks / dt:.2f}"
        )
        timed_text = tokens_to_timestamped_text(
            utterance_tokens,
            self.tokenizer,
            self.mimi.frame_rate,
            end_of_padding_id=0,
            padding_token_id=padding_token_id,
            offset_seconds=int(n_prefix_chunks / self.mimi.frame_rate) + audio_delay_seconds,
        )
        # audio_data = sr.AudioData(bytes(data),
        #     16000,
        #     2
        # )
        # audio_file = 'player_recording.wav'
        # with open(audio_file, 'wb') as file:
        #     file.write(audio_data.get_wav_data(convert_rate=16000))
        

        print(timed_text)
        decoded = " ".join([str(t.text) for t in timed_text])
        return decoded