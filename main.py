import logging
import src.conversation_manager as cm
import src.config_loader as config_loader
import src.utils as utils
import threading

def setup_logging(file_name):
    logging.basicConfig(filename=file_name, format='%(asctime)s %(levelname)s: %(message)s', level=logging.INFO)
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    logging.getLogger('').addHandler(console)

config = config_loader.ConfigLoader() # Load config from config.json
utils.cleanup_mei(config.remove_mei_folders) # clean up old instances of exe runtime files
setup_logging(config.logging_file_path) # Setup logging with the file specified in config.json
# try:
# except Exception as e:
#     logging.error(f"Error loading config:")
#     logging.error(e)
#     input("Press Enter to exit.")
#     exit()

# try:
# except Exception as e:
#     logging.error(f"Error Creating Conversation Manager:")
#     logging.error(e)
#     input("Press Enter to exit.")
#     exit()

conversation_manager = cm.conversation_manager(config)
def conversation_loop():
    def restart_manager():
        global conversation_manager
        logging.info("Restarting conversation manager")
        conversation_manager = cm.conversation_manager(config)
    while True: # Main Conversation Loop - restarts when conversation ends
        conversation_manager.await_and_setup_conversation() # wait for player to select an NPC and setup the conversation when outside of conversation
        while conversation_manager.in_conversation and not conversation_manager.conversation_ended:
            conversation_manager.step() # step through conversation until conversation ends
            if conversation_manager.restart:
                restart_manager()
                break
        if conversation_manager.restart:
            restart_manager()

        # try: # Main Conversation Loop - restarts when conversation ends
        # except Exception as e:
        #     try:
        #         conversation_manager.game_state_manager.write_game_info('_mantella_status', 'Error with Mantella.exe. Please check MantellaSoftware/logging.log')
        #     except:
        #         None
        #     logging.error(f"Error in main.py:")
        #     logging.error(e)
        #     print(e)
        #     input("Press Enter to exit.")
        #     exit()
            
# Start config flask server and conversation loop in parallel
if config.ready:
    thread1 = threading.Thread(target=config.host_config_server, args=(), daemon=True)
    thread1.start()
    conversation_loop()
else:
    config.host_config_server()