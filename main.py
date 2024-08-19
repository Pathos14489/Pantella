from src.logging import logging
import os
print(os.path.dirname(__file__))
import src.conversation_manager as cm
import src.config_loader as config_loader
import src.utils as utils
import threading
import traceback
try:
    import gradio as gr
    imported_gradio = True
except Exception as e:
    logging.error(f"Error importing gradio:")
    logging.error(e)
    imported_gradio = False

logging.info("Starting Pantella...")
try:
    config = config_loader.ConfigLoader() # Load config from config.json
except Exception as e:
    logging.error(f"Error loading config:")
    logging.error(e)
    tb = traceback.format_exc()
    logging.error(tb)
    input("Press Enter to exit.")
    raise e


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

        # mem_thread = threading.Thread(target=mem_gr_blocks.launch, kwargs={'share':config.share_debug_ui, 'server_port':config.memory_editor_port, "prevent_thread_lock":True})
        # mem_thread.start()
        mem_gr_blocks.launch(share=config.share_debug_ui, server_port=config.memory_editor_port, prevent_thread_lock=True)
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
    with gr.Blocks() as mem_gr_blocks:
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
        conversation_manager.assign_gradio_blocks(mem_gr_blocks, title_label, npc_selector, current_location, player_name, player_race, player_sex, npc_add_button, chat_box, chat_input, retry_button, latest_voice_line)
elif config.debug_mode and not imported_gradio:
	logging.error("Could not import gradio. Please install gradio to use the debug UI.")
	input("Press Enter to exit.")
	raise Exception("Could not import gradio. Please install gradio to use the debug UI.")

def conversation_loop():
    def restart_manager():
        global conversation_manager
        logging.info("Restarting conversation manager")
        conversation_manager = cm.create_manager(config)
        if not config.debug_mode and (config.game_id == "skyrim" or config.game_id == "skyrimvr" or config.game_id == "fallout4" or config.game_id == "fallout4vr"):
            conversation_manager.game_state_manager.write_game_info('_pantella_status', 'Restarted Pantella')
    while True: # Main Conversation Loop - restarts when conversation ends
        conversation_manager.await_and_setup_conversation() # wait for player to select an NPC and setup the conversation when outside of conversation
        while conversation_manager.in_conversation and not conversation_manager.conversation_ended:
            conversation_manager.step() # step through conversation until conversation ends
            if conversation_manager.restart:
                restart_manager()
                break
        if conversation_manager.restart:
            restart_manager()
            
# Start config flask server and conversation loop in parallel
if config.ready:
    if config.debug_mode:
        thread1 = threading.Thread(target=mem_gr_blocks.launch, kwargs={'share':config.share_debug_ui, 'server_port':config.debug_ui_port, "prevent_thread_lock":True})
        thread1.start()
        logging.info("Debug UI started -- WARNING: In Game Conversations will not work in Debug Mode, if you're trying to start a conversation and getting a bug in game, this is why. Turn debug mode off to talk to NPCs in game!")
        conversation_loop()
    else:
        thread1 = threading.Thread(target=config.host_config_server, args=(), daemon=True)
        thread1.start()
        conversation_loop()
else:
    config.host_config_server()