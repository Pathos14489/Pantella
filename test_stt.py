
from  src.logging import logging
import os
print(os.path.dirname(__file__))
import traceback

from src.stt import create_Transcriber

# Fake config for testing
class FakeConfig:
    def __init__(self):
        # STT settings
        self.stt_enabled = True
        self.stt_engine = "faster_whisper" # Change this to test different STT engines
        self.stt_language = "default"
        self.speech_processor = "silero_vad" # Change this to test different Speech Input Processors
        self.audio_threshold = "auto"
        self.pause_threshold = 0.5
        self.listen_timeout = 30.0
        self.manager_types = {}
        # Whisper specific settings
        self.whisper_model = "base"
        # faster_whisper specific settings
        self.stt_translate = False
        self.whisper_process_device = "cpu"
        self.whisper_cpu_threads = 4
        self.whisper_compute_type = "auto"
        self.beam_size = 5
        self.vad_filter = True

# Fake conversation manager for testing
class FakeConversationManager:
    def __init__(self, config):
        self.config = config

# Fake game interface for testing
class FakeGameInterface:
    def __init__(self, config):
        self.config = config
        self.conversation_manager = FakeConversationManager(config)

    def check_mic_status(self):
        return True
    
    def display_status(self, status):
        print(f"Game Interface Status: {status}")

transcriber = create_Transcriber(FakeGameInterface(FakeConfig()))

print("Starting STT Test Loop. Say 'exit' to quit.")
while True:
    try:
        transcription = transcriber.recognize_input([])
        if transcription.lower().strip() == "exit":
            break
        print(f"Transcription: {transcription}")
    except Exception as e:
        logging.error(f"Error during transcription:")
        logging.error(e)
        tb = traceback.format_exc()
        logging.error(tb)
        input("Press Enter to continue...")