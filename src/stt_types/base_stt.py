print('Loading base_stt.py...')
from src.logging import logging
try:
    logging.info('Importing speech_recognition in base_stt.py...')
    import speech_recognition as sr
except ImportError:
    logging.error('Could not import speech_recognition in base_stt.py. Please ensure the speech_recognition package is installed and try again.')
    raise ImportError('Could not import speech_recognition in base_stt.py. Please ensure the speech_recognition package is installed and try again.')
logging.info('Imported required libraries in base_stt.py')

stt_slug = "base_stt"

class base_Transcriber:
    def __init__(self, game_interface):
        global stt_slug
        self.stt_slug = stt_slug
        self.game_interface = game_interface
        self.conversation_manager = self.game_interface.conversation_manager
        self.config = self.conversation_manager.config
        self.language = self.config.stt_language
        self.available_languages = ["af","am","ar","as","az","ba","be","bg","bn","bo","br","bs","ca","cs","cy","da","de","el","en","es","et","eu","fa","fi","fo","fr","gl","gu","ha","haw","he","hi","hr","ht","hu","hy","id","is","it","ja","jw","ka","kk","km","kn","ko","la","lb","ln","lo","lt","lv","mg","mi","mk","ml","mn","mr","ms","mt","my","ne","nl","nn","no","oc","pa","pl","ps","pt","ro","ru","sa","sd","si","sk","sl","sn","so","sq","sr","su","sv","sw","ta","te","tg","th","tk","tl","tr","tt","uk","ur","uz","vi","yi","yo","zh","yue"]
        if self.language == 'auto' or self.language == 'default' or self.language not in self.available_languages:
            self.language = "en"

        self.audio_threshold = self.config.audio_threshold
        self.listen_timeout = self.config.listen_timeout
        self.pause_threshold = self.config.pause_threshold
        self.initialized = False
        if self.game_interface.check_mic_status(): # if mic is enabled on __init__, pre-initialize recognizer and microphone
            self.initialize()

    def initialize(self):
        logging.info('Initializing speech recognizer...')
        self.recognizer = sr.Recognizer()
        self.recognizer.pause_threshold = self.pause_threshold
        self.microphone = sr.Microphone()

        if self.audio_threshold == 'auto':
            logging.info(f"Audio threshold set to 'auto'. Adjusting microphone for ambient noise...")
            logging.info("If the mic is not picking up your voice, try setting this audio_threshold value manually in PantellaSoftware/config.json.\n")
            with self.microphone as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=5)
        else:
            self.recognizer.dynamic_energy_threshold = False
            self.recognizer.energy_threshold = int(self.audio_threshold)
            logging.info(f"Audio threshold set to {self.audio_threshold}. If the mic is not picking up your voice, try lowering this value in PantellaSoftware/config.json. If the mic is picking up too much background noise, try increasing this value.\n")
        self.initialized = True
        logging.info('Speech recognizer initialized')
    
    def unload(self):
        logging.info('Unloading speech recognizer...')
        self.initialized = False
        del self.recognizer
        del self.microphone