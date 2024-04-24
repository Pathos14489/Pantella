from  src.logging import logging
import os
print(os.path.dirname(__file__))
import src.conversation_manager as cm
import src.config_loader as config_loader
import src.utils as utils
import threading
import gradio as gr


print("Starting Pantella - Debug UI")
try:
    config = config_loader.ConfigLoader() # Load config from config.json
except Exception as e:
    logging.error(f"Error loading config:")
    logging.error(e)
    input("Press Enter to exit.")
    raise e

utils.cleanup_mei(config.remove_mei_folders) # clean up old instances of exe runtime files

config.conversation_manager_type = "gradio" # override conversation manager type to gradio
config.interface_type = "gradio" # override game interface type to gradio
config.sentences_per_voiceline = 99 # override sentences per voiceline to 99 so all outputs generate the whole voice line instead of parts

print("Creating Conversation Manager")
try:
    conversation_manager = cm.create_manager(config)
except Exception as e:
    logging.error(f"Error Creating Conversation Manager:")
    logging.error(e)
    input("Press Enter to exit.")
    raise e

with gr.Blocks() as gr_blocks:
    title_label = gr.Label("Pantella - Debug UI")
    with gr.Row():
        # Selector for the player to choose an NPC to add to the conversation and button to add the NPC to the conversation
        with gr.Column(scale=0.5):
            npc_values = []
            for character in conversation_manager.character_database._characters:
                npc_values.append((f"{character['name']}",character))
            logging.info(f"NPCs ready for conversation: {len(npc_values)}")
            npc_selector = gr.Dropdown(npc_values, multiselect=False, label="NPC in Conversation:")
            current_location = gr.Textbox("Skyrim", label="Location Description")
            player_name = gr.Textbox("Adven", label="Player Name")
            player_race = gr.Textbox("Nord", label="Player Race")
            player_sex = gr.Dropdown(["Male","Female"], label="Player Sex")
            npc_add_button = gr.Button(value="Start Conversation")
        # Chat box for the player to type in their responses
        with gr.Column():
            latest_voice_line = gr.Audio(interactive=False, label="Latest Voice Line",autoplay=True)
            chat_box = gr.Chatbot()
            chat_input = gr.Textbox("Hello there.", label="Chat Input", placeholder="Type a message...")
    conversation_manager.assign_gradio_blocks(gr_blocks, title_label, npc_selector, current_location, player_name, player_race, player_sex, npc_add_button, chat_box, chat_input, latest_voice_line)
    # conversation_manager.await_and_setup_conversation()
    # gr_blocks.launch()

def conversation_loop():
    def restart_manager():
        global conversation_manager
        logging.info("Restarting conversation manager")
        conversation_manager = cm.create_manager(config)
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
thread1 = threading.Thread(target=gr_blocks.launch, args=(), daemon=True)
thread1.start()
conversation_loop()