
from  src.logging import logging
import os
print(os.path.dirname(__file__))
import src.conversation_manager as cm
import src.config_loader as config_loader
import src.utils as utils
import argparse
import src.character_db as character_db
import json
import traceback
import src.tts as tts

print("Starting Pantella TTS Test Script")
    
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Test TTS')
    parser.add_argument('--initialize', action='store_true', help='Initialize the conversation manager')
    args = parser.parse_args()
    try:
        config = config_loader.ConfigLoader() # Load config from config.json
    except Exception as e:
        logging.error(f"Error loading config:")
        logging.error(e)
        tb = traceback.format_exc()
        logging.error(tb)
        input("Press Enter to exit.")
        raise e

    utils.cleanup_mei(config.remove_mei_folders) # clean up old instances of exe runtime files
    
    print("Creating Conversation Manager")
    try:
        conversation_manager = cm.create_manager(config, initialize=args.initialize) # Partially load conversation manager
    except Exception as e:
        logging.error(f"Error Creating Conversation Manager:")
        logging.error(e)
        tb = traceback.format_exc()
        logging.error(tb)
        input("Press Enter to exit.")
        raise e
    voice_model = "MaleNord"
    while True:
        user_input = input("Enter text to convert to speech: ")
        command, command_input = user_input.split(" ", 1)
        if command == "exit":
            break
        elif command == "change_tts":
            ttses = command_input.split(",")
            if type(ttses) == str:
                ttses = [ttses]
            conversation_manager.synthesizer = tts.create_Synthesizer(conversation_manager, ttses)
        elif command == "change_voice":
            voice_model = command_input
        else:
            try:
                conversation_manager.synthesizer._say(user_input, voice_model)
            except Exception as e:
                logging.error(f"Error saying text '{user_input}' with voice model '{voice_model}'")
                logging.error(e)
                tb = traceback.format_exc()
                logging.error(tb)
                input("Press Enter to exit.")
                raise e