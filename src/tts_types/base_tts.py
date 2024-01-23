
import logging
import src.utils as utils

class VoiceModelNotFound(Exception):
    pass

tts_slug = "base_Synthesizer"
class base_Synthesizer:
    def __init__(self, conversation_manager):
        self.conversation_manager = conversation_manager
        self.config = self.conversation_manager.config
        # currrent game running
        self.game = self.config.game_id
        # output wav / lip files path
        self.output_path = utils.resolve_path('data')+'/data'
        self.language = self.config.language
    
    def voices(self):
        logging.info("Warning: Using voice() method of base_tts.py, this means you haven't implemented the voices() method in your new tts type. This method should return a list of available voices models for the current game from the tts.")
        input("Press enter to continue...")
        exit(0)
        return []

    @utils.time_it
    def change_voice(self, character):
        voice = character.voice_model
        logging.info(f'Warning: Using change_voice() method of base_tts.py, this means you haven\'t implemented the change_voice() method in your new tts type. This method should change the voice of the tts to the voice model specified in the character object.')
        logging.info(f'Changing voice to: {voice}')
        self.last_voice = voice
        logging.info('Voice model not loaded, please fix your code.')
        input("Press enter to continue...")
        exit(0)
        return None

    @utils.time_it
    def synthesize(self, text, character, **kwargs):
        logging.info(f'Warning: Using synthesizer() method of base_tts.py, this means you haven\'t implemented the synthesizer() method in your new tts type. This method should synthesize the text passed as a parameter with the voice model specified in the character object.')
        logging.info(f'Synthesizing text: {text}')
        logging.info(f'Using voice model: {character.voice_model}')
        logging.info('Using Additional parameters: {}'.format(kwargs))
        logging.info('Wav file not saved, please fix your code.')
        logging.info('Lip file not saved, please fix your code.')
        logging.info('Voice model not loaded, please fix your code.')
        input("Press enter to continue...")
        exit(0)
        return final_voiceline_file # path to wav file
        