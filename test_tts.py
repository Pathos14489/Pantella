
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
from src.ui import root, OptionDialog

print("Starting Pantella TTS Test Script")
    
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Test TTS')
    parser.add_argument('--initialize', action='store_true', help='Initialize the conversation manager')
    args = parser.parse_args()


    def get_interface():
        root.deiconify() # show the root window so the dialog shows up, we'll hide it again after the dialog is closed
        available_interfaces = config_loader.interface_configs.keys()
        dlg = OptionDialog(root, "Select Interface", "Select the game interface to use with Pantella. You can change this later in the config.json file or by using the web configurator.", available_interfaces)
        root.withdraw() # hide the root window again after the dialog is closed
        return dlg.result   
    
    selected_interface = get_interface()
    os.makedirs(os.path.join(os.path.dirname(__file__), "configs"), exist_ok=True) # make configs directory if it doesn't exist
    config_path = os.path.join(os.path.dirname(__file__), "configs", f"{selected_interface}_config.json")
    if not os.path.exists(config_path):
        logging.error(f"No config found for default interface '{selected_interface}' at path: {config_path}, exiting.")

    try:
        config = config_loader.ConfigLoader(config_path, selected_interface) # Load config from config.json
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
        user_input_parts = user_input.split(" ", 1)
        if len(user_input_parts) == 2:
            command, command_input = user_input.split(" ", 1)
        else:
            command = user_input
            command_input = ""
        if command == "exit":
            break
        elif command == "change_tts":
            ttses = command_input.split(",")
            if type(ttses) == str:
                ttses = [ttses]
            conversation_manager.synthesizer = tts.create_Synthesizer(conversation_manager, ttses)
        elif command == "change_voice":
            voice_model = command_input
        elif command == "test_all_voices":
            for voice in conversation_manager.synthesizer.voices():
                logging.info(f"Testing voice: {voice}")
                try:
                    conversation_manager.synthesizer._say("This is a test of the " + voice + " voice.", voice)
                except Exception as e:
                    logging.error(f"Error saying text with voice model '{voice}'")
                    logging.error(e)
                    tb = traceback.format_exc()
                    logging.error(tb)
        else:
            if command_input.strip() == "":
                logging.warning("No text provided to synthesize!")
                continue
            try:
                conversation_manager.synthesizer._say(user_input, voice_model)
            except Exception as e:
                logging.error(f"Error saying text '{user_input}' with voice model '{voice_model}'")
                logging.error(e)
                tb = traceback.format_exc()
                logging.error(tb)
                input("Press Enter to exit.")
                raise e