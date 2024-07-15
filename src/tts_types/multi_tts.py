print("Loading multi_tts.py...")
from src.logging import logging
import src.tts_types.base_tts as base_tts
logging.info("Imported required libraries in multi_tts.py")

tts_slug = "multi_tts"
class Synthesizer(base_tts.base_Synthesizer):
    def __init__(self, conversation_manager, ttses = []):
        super().__init__(conversation_manager)
        self.tts_engines = ttses
        fallback_order = ""
        for tts, tts_index in enumerate(self.tts_engines):
            fallback_order += f"{tts_index}. {tts.tts_slug}\n"
        logging.config(f"Loaded multi_tts with tts engines in the following fallback order:\n{fallback_order}")

    def voices(self):
        """Return a list of available voices"""
        voices = []
        for tts in self.tts_engines:
            voices += tts.voices()
        voices = list(set(voices))
        return voices
    
    def get_valid_voice_model(self, character, crashable=False):
        """Synthesize the text for the character specified using either the 'tts_override' property of the character or using the first tts engine that supports the voice model of the character"""
        tts = None
        # print(voiceline)
        # print(character)
        if "tts_override" in character.__dict__:
            for tts_engine in self.tts_engines:
                if character.tts_override == tts_engine.tts_slug and tts_engine.get_valid_voice_model(character) != None:
                    tts = tts_engine
                elif tts_engine.get_valid_voice_model(character) != None:
                    tts = tts_engine
        else:
            for tts_engine in self.tts_engines:
                if tts_engine.get_valid_voice_model(character) != None:
                    tts = tts_engine
        if tts is None:
            logging.error(f"Could not find tts engine for voice model: {character.voice_model}! Please check your config.json file and try again!")
            if self.crashable:
                input("Press enter to continue...")
                raise ValueError(f"Could not find tts engine for voice model: {character.voice_model}! Please check your config.json file and try again!")
        else:
            return tts.get_valid_voice_model(character, crashable=crashable)
    
    def synthesize(self, voiceline, character, **kwargs):
        """Synthesize the text for the character specified using either the 'tts_override' property of the character or using the first tts engine that supports the voice model of the character"""
        tts = None
        # print(voiceline)
        # print(character)
        if "tts_override" in character.__dict__:
            for tts_engine in self.tts_engines:
                if character.tts_override == tts_engine.tts_slug and tts_engine.get_valid_voice_model(character) != None:
                    tts = tts_engine
                    break
                if tts_engine.get_valid_voice_model(character) != None:
                    tts = tts_engine
                    break
        else:
            for tts_engine in self.tts_engines:
                if tts_engine.get_valid_voice_model(character) != None:
                    tts = tts_engine
                    break
        if tts is None:
            logging.error(f"Could not find tts engine for voice model: {character.voice_model}! Please check your config.json file and try again!")
            if self.crashable:
                input("Press enter to continue...")
                raise ValueError(f"Could not find tts engine for voice model: {character.voice_model}! Please check your config.json file and try again!")
        else:
            return tts.synthesize(voiceline, character, **kwargs)
        
    def _say(self, voiceline, voice_model="Female Sultry", volume=0.5):
        tts = None
        for tts_engine in self.tts_engines:
            if tts_engine.get_valid_voice_model(voice_model) != None:
                tts = tts_engine
                break
        if tts is None:
            logging.error(f"Could not find tts engine for voice model: {voice_model}! Please check your config.json file and try again!")
            if self.crashable:
                input("Press enter to continue...")
                raise ValueError(f"Could not find tts engine for voice model: {voice_model}! Please check your config.json file and try again!")
        else:
            return tts._say(voiceline, voice_model=voice_model, volume=volume)