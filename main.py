import logging
import src.conversation_manager as cm

conversation_manager = cm.conversation_manager(config_file='config.ini', logging_file='logging.log', secret_key_file='GPT_SECRET_KEY.txt', language_file='data/language_support.csv')
# try:
# except Exception as e:
#     logging.error(f"Error Creating Conversation Manager:")
#     logging.error(e)
#     print(e)
#     input("Press Enter to exit.")
#     exit()

while True: # Main Conversation Loop - restarts when conversation ends
    conversation_manager.await_and_setup_conversation() # wait for player to select an NPC and setup the conversation when outside of conversation
    while conversation_manager.in_conversation:
        conversation_manager.step() # step through conversation until conversation ends
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