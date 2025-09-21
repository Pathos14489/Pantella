print('Loading speech_recognition.py...')
from src.logging import logging
import io
import numpy as np
import time
from src.speech_input_processor_types.base_Speech_Input_Processor import base_Speech_Input_Processor
speech_recognition_imported = False
try:
    logging.info('Importing required libraries in silero_vad.py...')
    import torch
    torch.set_num_threads(1)
    import torchaudio
    import pyaudio
    import speech_recognition as sr
except ImportError:
    logging.error('Could not import required libraries in silero_vad.py. Please ensure all required packages are installed and try again.')
    raise ImportError('Could not import required libraries in silero_vad.py. Please ensure all required packages are installed and try again.')
logging.info('Imported required libraries in silero_vad.py')

speech_input_processor_slug = "silero_vad"

class Speech_Input_Processor(base_Speech_Input_Processor):
    def __init__(self, transcriber):
        global speech_input_processor_slug
        super().__init__(transcriber)
        self.stt_slug = speech_input_processor_slug

        logging.info('Initializing silero_vad...')
        

        self.model, self.utils = torch.hub.load(repo_or_dir='snakers4/silero-vad',
            model='silero_vad',
            force_reload=True
        )
        (self.get_speech_timestamps,
        self.save_audio,
        self.read_audio,
        self.VADIterator,
        self.collect_chunks) = self.utils

        self.FORMAT = pyaudio.paInt16
        self.CHANNELS = 1
        self.SAMPLE_RATE = 16000
        self.CHUNK = int(self.SAMPLE_RATE / 10)
        
        self.pause_threshold = self.config.pause_threshold
        self.confidence_threshold = 0.5

        logging.info('silero_vad initialized')

    def validate(self, inputs: torch.Tensor):
        with torch.no_grad():
            outs = self.model(inputs)
        return outs

    # Provided by Alexander Veysov to silero_vad repo
    def int2float(self, sound):
        abs_max = np.abs(sound).max()
        sound = sound.astype('float32')
        if abs_max > 0:
            sound *= 1/32768
        sound = sound.squeeze()  # depends on the use case
        return sound

    def get_audio_from_mic(self) -> bytes:
        """Gets audio from the microphone and returns the audio data"""
        audio = pyaudio.PyAudio()
        num_samples = 512
        stream = audio.open(format=self.FORMAT,
            channels=self.CHANNELS,
            rate=self.SAMPLE_RATE,
            input=True,
            frames_per_buffer=self.CHUNK,
        )

        print("Started Recording")
        done_speaking = False
        started_speaking = False
        last_spoke_time = None
        data = bytearray()
        empty_buffer_count = 4
        empty_buffer = []
        while not done_speaking:
            try:
                audio_chunk = stream.read(num_samples)
            except Exception as e:
                time.sleep(0.1)
                audio_chunk = stream.read(num_samples)

            audio_int16 = np.frombuffer(audio_chunk, np.int16)

            audio_float32 = self.int2float(audio_int16)
            
            # get the confidences and add them to the list to plot them later
            new_confidence = self.model(torch.from_numpy(audio_float32), 16000).item()
            if new_confidence > self.confidence_threshold:
                if not started_speaking:
                    logging.debug(f"Voice detected with confidence {new_confidence}")
                    # add the empty buffer to the data
                    for chunk in empty_buffer:
                        data.extend(chunk)
                    empty_buffer = []
                started_speaking = True
                data.extend(audio_chunk)
                last_spoke_time = time.time()
            elif not started_speaking:
                empty_buffer.append(audio_chunk)
                if len(empty_buffer) > empty_buffer_count:
                    empty_buffer.pop(0) 
            if started_speaking and last_spoke_time is not None and (time.time() - last_spoke_time) > self.pause_threshold:
                done_speaking = True
                logging.debug(f"Stopping recording after {self.pause_threshold} seconds of silence")
        stream.stop_stream()
        stream.close()
        audio.terminate()
        print("Stopped the recording")
        audio_data = sr.AudioData(bytes(data),
            16000,
            2
        )
        return audio_data.get_wav_data(convert_rate=16000)