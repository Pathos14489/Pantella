from src.logging import logging
logging.info("Importing main.py")
import os
import src.conversation_manager as cm
import src.config_loader as config_loader
import src.utils as utils
import threading
import random
import traceback
import asyncio
import webbrowser
import time
import json

logging.info("Imported required libraries in main.py")

from tkinter import Tk, Label
from src.ui import root, OptionDialog


def get_interface():
    root.deiconify() # show the root window so the dialog shows up, we'll hide it again after the dialog is closed
    available_interfaces = config_loader.interface_configs.keys()
    dlg = OptionDialog(root, "Select Interface", "Select the game interface to use with Pantella. You can change this later in the config.json file or by using the web configurator.", available_interfaces)
    root.withdraw() # hide the root window again after the dialog is closed
    return dlg.result
def ask_always_open_interface_selection():
    root.deiconify() # show the root window so the dialog shows up, we'll hide it again after the dialog is closed
    dlg = OptionDialog(root, "Always Open Interface Selection?", "Do you want to always open the interface selection dialog on startup? You can change this later in the startup.json file.", ["Yes", "No"])
    root.withdraw() # hide the root window again after the dialog is closed
    return dlg.result == "Yes"
def get_default_interface():
    root.deiconify() # show the root window so the dialog shows up, we'll hide it again after the dialog is closed
    available_interfaces = config_loader.interface_configs.keys()
    dlg = OptionDialog(root, "Select Default Interface", "Select the default game interface to use with Pantella. This will be the default interface used on startup if 'Always Open Interface Selection' is set to false. You can change this later in the startup.json file.", available_interfaces)
    root.withdraw() # hide the root window again after the dialog is closed
    return dlg.result


if __name__ == "__main__":
    try:
        import gradio as gr
        imported_gradio = True
    except Exception as e:
        logging.error(f"Error importing gradio:")
        logging.error(e)
        imported_gradio = False

    startup_config = {
        "default_interface": "",
        "always_open_interface_selection": True,
        "first_time_setup": True
    }
    if os.path.exists(os.path.join(os.path.dirname(__file__), "startup.json")):
        try:
            with open(os.path.join(os.path.dirname(__file__), "startup.json"), "r") as f:
                startup_config = json.load(f)
        except Exception as e:
            logging.error(f"Error loading startup config, deleting startup config and starting fresh:")
            logging.error(e)
            os.remove(os.path.join(os.path.dirname(__file__), "startup.json"))


    if startup_config.get("first_time_setup", True):
        startup_config["first_time_setup"] = False
        with open(os.path.join(os.path.dirname(__file__), "startup.json"), "w") as f:
            json.dump(startup_config, f)
        always_open = ask_always_open_interface_selection()
        startup_config["always_open_interface_selection"] = always_open
        if not always_open:
            default_interface = get_default_interface()
            if default_interface is None or default_interface == "":
                logging.error("No default interface selected, exiting.")
                input("Press Enter to exit.")
                exit()
            startup_config["default_interface"] = default_interface
        with open(os.path.join(os.path.dirname(__file__), "startup.json"), "w") as f:
            json.dump(startup_config, f)
            
    if startup_config.get("always_open_interface_selection", False) or startup_config.get("default_interface", "") == "":
        selected_interface = get_interface()
        if selected_interface is None or selected_interface == "":
            logging.error("No default interface selected, exiting.")
            input("Press Enter to exit.")
            exit()
    else:
        selected_interface = startup_config.get("default_interface", "")
        logging.info(f"Default interface selected from startup config: {selected_interface}")

    os.makedirs(os.path.join(os.path.dirname(__file__), "configs"), exist_ok=True) # make configs directory if it doesn't exist

    config_path = os.path.join(os.path.dirname(__file__), "configs", f"{selected_interface}_config.json")
    if not os.path.exists(config_path):
        logging.error(f"No config found for default interface '{selected_interface}' at path: {config_path}, exiting.")
        


    logging.info("Starting Pantella...")
    try:
        config = config_loader.ConfigLoader(config_path, selected_interface) # Load config from config.json
    except Exception as e:
        logging.error(f"Error loading config:")
        logging.error(e)
        tb = traceback.format_exc()
        logging.error(tb)
        input("Press Enter to exit.")
        raise e
    if config.seed != -1:
        seed = config.seed # set random seed for reproducibility
    else:
        seed = time.time() # set random seed to current time
    random.seed(seed)
    logging.info(f"Pantella Seed: {seed}")

    logging.info("Loading blocked logging paths -- No logs will be generated from these files")
    logging.block_logs_from = config.block_logs_from # block logs from certain files

    utils.cleanup_mei(config.remove_mei_folders) # clean up old instances of exe runtime files

    if config.chromadb_memory_editor_enabled and imported_gradio:
        from src.chromadb_memory_editor import MemoryEditor, get_player_ids, get_npc_ids, game_ids, game_selected, player_selected, npc_selected, delete_memory, save_memories, me
        logging.info("Starting Memory Editor...")
        with gr.Blocks() as mem_gr_blocks:
            title_label = gr.Label("Pantella - Memory Editor")
            with gr.Column():
                # Selector for the player to choose an NPC to add to the conversation and button to add the NPC to the conversation
                memories = gr.Dataframe(label="Memories", headers=["ID(WARNING, DON'T TOUCH)","Name","Content","Role","Timestamp","Location","Type"]+[f"{emotion} value" for emotion in me.config.emotion_composition]+["Conversation ID"], interactive=True, datatype=["str","str","str","str","str","str","str"]+["number"]*len([emotion for emotion in me.config.emotion_composition])+["str"], type="array", col_count=(6+2+len([emotion for emotion in me.config.emotion_composition]),"fixed"))
                with gr.Accordion(label="Controls"):
                    with gr.Row():
                        with gr.Column():
                            game_id_selector = gr.Dropdown(game_ids, multiselect=False, label="Game ID:")
                            player_id_selector = gr.Dropdown(get_player_ids(game_id_selector), multiselect=False, label="Player ID:")
                            npc_id_selector = gr.Dropdown(get_npc_ids(game_id_selector,player_id_selector), multiselect=False, label="NPC ID:")
                        with gr.Column():
                            with gr.Group():
                                selected_memory_id = gr.Textbox("", label="Selected Memory ID", placeholder="Enter Memory ID to Delete")
                                delete_button = gr.Button(value="Delete Memory", variant="stop")
                    save_button = gr.Button(value="Save Memories", variant="primary")
                
                game_id_selector.select(game_selected, inputs=[game_id_selector], outputs=[player_id_selector, npc_id_selector])
                player_id_selector.select(player_selected, inputs=[game_id_selector, player_id_selector], outputs=[npc_id_selector])
                npc_id_selector.select(npc_selected, inputs=[game_id_selector, player_id_selector, npc_id_selector], outputs=[npc_id_selector, memories])
                # memories.select(select_memory, inputs=[memories], outputs=[selected_memory_id])
                delete_button.click(delete_memory, inputs=[game_id_selector, player_id_selector, npc_id_selector, selected_memory_id], outputs=[selected_memory_id, memories])
                save_button.click(save_memories, inputs=[game_id_selector, player_id_selector, npc_id_selector, memories])

            # mem_gr_blocks.launch(share=config.share_debug_ui, server_port=config.memory_editor_port, prevent_thread_lock=True)
            logging.info("Memory Editor started")

    if config.debug_mode:
        config.conversation_manager_type = "gradio" # override conversation manager type to gradio
        config.interface_type = "gradio" # override game interface type to gradio
        config.sentences_per_voiceline = 99 # override sentences per voiceline to 99 so all outputs generate the whole voice line instead of parts
        logging.info("Debug Mode Enabled -- Conversation Manager Type set to Gradio, Interface Type set to Gradio, Sentences Per Voiceline forced to 99")

    logging.info("Creating Conversation Manager")
    try:
        conversation_manager = cm.create_manager(config)
    except Exception as e:
        logging.error(f"Error Creating Conversation Manager:")
        logging.error(e)
        tb = traceback.format_exc()
        logging.error(tb)
        input("Press Enter to exit.")
        raise e

    if config.debug_mode and imported_gradio:
        with gr.Blocks() as debug_gr_blocks:
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
                    with gr.Row():
                        retry_button = gr.Button(value="Retry Conversation")
            conversation_manager.assign_gradio_blocks(debug_gr_blocks, title_label, npc_selector, current_location, player_name, player_race, player_sex, npc_add_button, chat_box, chat_input, retry_button, latest_voice_line)
    elif config.debug_mode and not imported_gradio:
        logging.error("Could not import gradio. Please install gradio to use the debug UI.")
        input("Press Enter to exit.")
        raise Exception("Could not import gradio. Please install gradio to use the debug UI.")

def restart_manager(conf, conv_manager):
    logging.info("Restarting conversation manager")
    conv_manager = cm.create_manager(conf)
    if not conf.debug_mode and (conf.game_id == "skyrim" or conf.game_id == "skyrimvr" or conf.game_id == "fallout4" or conf.game_id == "fallout4vr"):
        conv_manager.game_interface.pantella_restarted()
    return conv_manager

async def conversation_loop():
    global conversation_manager
    if config.open_config_on_startup:
        url = f"http://localhost:{config.config_port}/"
        webbrowser.open(url, new=0, autoraise=True)
    if config.play_startup_announcement:
        voices = conversation_manager.synthesizer.voices()
        if len(voices) == 0:
            logging.warning("No voices found for selected TTS, cannot play startup announcement.")
        else:
            random_voice = random.choice(voices)
            conversation_manager.synthesizer._say("Pantella is ready to go.", random_voice)
    while True: # Main Conversation Loop - restarts when conversation ends
        await conversation_manager.await_and_setup_conversation() # wait for player to select an NPC and setup the conversation when outside of conversation
        while conversation_manager.in_conversation and not conversation_manager.conversation_ended:
            await conversation_manager.step() # step through conversation until conversation ends
            if conversation_manager.restart:
                conversation_manager = restart_manager(config, conversation_manager)
                break
        if conversation_manager.restart:
            conversation_manager = restart_manager(config, conversation_manager)
            
if __name__ == "__main__":
    # Start config FastAPI server and conversation loop in parallel
    if config.ready:
        if imported_gradio:
            if config.chromadb_memory_editor_enabled:
                logging.info("Starting Memory Editor WebUI Thread")
                mem_thread = threading.Thread(target=mem_gr_blocks.launch, kwargs={'share':config.share_debug_ui, 'server_port':config.memory_editor_port, "prevent_thread_lock":True})
                mem_thread.start()
                logging.info(mem_thread)
                logging.info("Memory Editor WebUI started")
            if config.debug_mode:
                logging.info("Starting Debug WebUI Thread")
                debug_thread = threading.Thread(target=debug_gr_blocks.launch, kwargs={'share':config.share_debug_ui, 'server_port':config.debug_ui_port, "prevent_thread_lock":True})
                debug_thread.start()
                logging.info(debug_thread)
                logging.warn("Debug WebUI started -- WARNING: In Game Conversations will not work in Debug Mode, if you're trying to start a conversation and getting a bug in game, this is why. Turn debug mode off to talk to NPCs in game!")
        if config.web_configurator:
            logging.info("Starting Config WebUI Thread")
            config_thread = threading.Thread(target=config.host_config_server, kwargs={'conversation_manager': conversation_manager}, daemon=True)
            config_thread.start()
            logging.info(config_thread)
            logging.info("Config Server WebUI started")
        logging.info("Starting Conversation Loop")
        asyncio.run(conversation_loop())
    else:
        config.host_config_server()