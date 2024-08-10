from  src.logging import logging
import os
print(os.path.dirname(__file__))
import gradio as gr
import src.config_loader as config_loader
import json
import chromadb
import traceback
from chromadb.config import Settings
try:
    config = config_loader.ConfigLoader() # Load config from config.json
except Exception as e:
    logging.error(f"Error loading config:")
    logging.error(e)
    tb = traceback.format_exc()
    logging.error(tb)
    input("Press Enter to exit.")
    raise e

class MemoryEditor():
    def __init__(self,config):
        self.config = config
        self.conversation_history_directory = f"{self.config.conversation_data_directory}/"
        self.NPCs = []
        for game_id_directory in os.listdir(self.conversation_history_directory):
            if not game_id_directory.startswith("."):
                for player_directory in os.listdir(f"{self.conversation_history_directory}/{game_id_directory}"):
                    if not player_directory.startswith("."):
                        for npc_directory in os.listdir(f"{self.conversation_history_directory}/{game_id_directory}/{player_directory}"):
                            chroma_path = f"{self.conversation_history_directory}/{game_id_directory}/{player_directory}/{npc_directory}/chromadb"
                            self.NPCs.append({
                                "game_id": game_id_directory,
                                "player": player_directory,
                                "npc": npc_directory,
                                "chroma_path": chroma_path
                            })

    def get_memories(self, npc={
        "game_id": "",
        "player": "",
        "npc": ""
    }):
        game_id_directory = npc["game_id"]
        player_directory = npc["player"]
        npc_directory = npc["npc"]
        chroma_path = f"{self.conversation_history_directory}/{game_id_directory}/{player_directory}/{npc_directory}/chromadb"
        if not os.path.exists(chroma_path):
            logging.error(f"ChromaDB path does not exist: {chroma_path}")
            return
        logging.info(f"Loading NPC Memories for Game ID: {game_id_directory}, Player: {player_directory}, NPC: {npc_directory}")
        chroma_client = chromadb.PersistentClient(chroma_path,Settings(anonymized_telemetry=False))
        messages_memories = chroma_client.get_or_create_collection(name="messages")
        messages = messages_memories.get()
        logging.info(f"Loaded NPC Memories for Game ID: {game_id_directory}, Player: {player_directory}, NPC: {npc_directory}, Messages: {len(messages['ids'])}")
        msgs = []
        for i in range(len(messages["documents"])):
            msg_doc = messages["documents"][i]
            metadata = messages["metadatas"][i]
            id = messages["ids"][i]
            emotions = {}
            for emotion in self.config.emotion_composition:
                if emotion in metadata:
                    emotions[emotion] = metadata[emotion]
            msg = {
                "role": metadata["role"],
                "timestamp": metadata["timestamp"],
                "location": metadata["location"],
                "type": "memory", # "message" or "memory"
                "content": msg_doc,
                "emotions": emotions,
                "id": id,
                "conversation_id": metadata["conversation_id"],
            }
            if "name" in metadata:
                msg["name"] = metadata["name"]
            else:
                msg["name"] = ""
            msg["name"] = msg["name"].replace("[player]",player_directory.split("_")[2])
            msgs.append(msg)
        msgs.sort(key=lambda x: x["timestamp"])
        return chroma_client, messages_memories, msgs


me = MemoryEditor(config)
game_ids = []
for npc in me.NPCs:
    game_ids.append(f"{npc['game_id']}")
game_ids = list(set(game_ids))
def get_player_ids(game_id):
    player_ids = []
    for npc in me.NPCs:
        if npc["game_id"] == game_id:
            player_ids.append(f"{npc['player']}")
    player_ids = list(set(player_ids))
    return player_ids
def get_npc_ids(game_id,player_id):
    npc_ids = []
    for npc in me.NPCs:
        if npc["game_id"] == game_id and npc["player"] == player_id:
            npc_ids.append(f"{npc['npc']}")
    npc_ids = list(set(npc_ids))
    return npc_ids

def game_selected(game_id):
    print(game_id)
    new_player_id_selector = gr.Dropdown(get_player_ids(game_id), multiselect=False, label="Player ID:")
    new_npc_id_selector = gr.Dropdown(multiselect=False, label="NPC ID:")
    return new_player_id_selector, new_npc_id_selector

def player_selected(game_id, player_id):
    print(game_id, player_id)
    new_npc_id_selector = gr.Dropdown(get_npc_ids(game_id,player_id), multiselect=False, label="NPC ID:")
    return new_npc_id_selector

def npc_selected(game_id, player_id, npc_id):
    print(game_id,player_id,npc_id)
    npc = {
        "game_id": game_id,
        "player": player_id,
        "npc": npc_id
    }
    chroma_client, messages_memories, msgs = me.get_memories(npc)
    print(len(msgs),"messages loaded")
    # convert messages to list of tuples
    messages = []
    for msg in msgs:
        msg_tuple_parts = [msg["id"],msg["name"],msg["content"],msg["role"],msg["timestamp"],msg["location"],msg["type"]]
        for emotion in me.config.emotion_composition:
            if emotion in msg["emotions"]:
                msg_tuple_parts.append(msg["emotions"][emotion])
            else:
                msg_tuple_parts.append(0)
        msg_tuple_parts.append(msg["conversation_id"])
        msg_tuple = tuple(msg_tuple_parts)
        messages.append(msg_tuple)
    memories = gr.Dataframe(messages,label="Memories", headers=["ID(WARNING, DON'T TOUCH)","Name","Content","Role","Timestamp","Location","Type"]+[f"{emotion} value" for emotion in me.config.emotion_composition]+["Conversation ID"], interactive=True, datatype=["str","str","str","str","str","str"]+["number"]*len([emotion for emotion in me.config.emotion_composition])+["str"], type="array", col_count=(6+2+len([emotion for emotion in me.config.emotion_composition]),"fixed"))
    return npc_id, memories

def delete_memory(game_id, player_id, npc_id, selected_memory_id):
    print(selected_memory_id)
    npc = {
        "game_id": game_id,
        "player": player_id,
        "npc": npc_id
    }
    chroma_client, messages_memories, msgs = me.get_memories(npc)
    messages_memories.delete(ids=[selected_memory_id])
    messages = []
    for msg in msgs:
        msg_tuple_parts = [msg["id"],msg["name"],msg["content"],msg["role"],msg["timestamp"],msg["location"],msg["type"]]
        for emotion in me.config.emotion_composition:
            if emotion in msg["emotions"]:
                msg_tuple_parts.append(msg["emotions"][emotion])
            else:
                msg_tuple_parts.append(0)
        msg_tuple_parts.append(msg["conversation_id"])
        msg_tuple = tuple(msg_tuple_parts)
        messages.append(msg_tuple)
    memories = gr.Dataframe(messages,label="Memories", headers=["ID(WARNING, DON'T TOUCH)","Name","Content","Role","Timestamp","Location","Type"]+[f"{emotion} value" for emotion in me.config.emotion_composition]+["Conversation ID"], interactive=True, datatype=["str","str","str","str","str","str"]+["number"]*len([emotion for emotion in me.config.emotion_composition])+["str"], type="array", col_count=(6+2+len([emotion for emotion in me.config.emotion_composition]),"fixed"))
    return "", memories

def save_memories(game_id, player_id, npc_id, memories):
    npc = {
        "game_id": game_id,
        "player": player_id,
        "npc": npc_id
    }
    chroma_client, messages_memories, _ = me.get_memories(npc)
    # print(memories) # list of lists
    # convert messages to list of dicts
    msgs = []
    for msg in memories:
        # msg_dict should be like this: {
        #     "role": metadata["role"],
        #     "timestamp": metadata["timestamp"],
        #     "location": metadata["location"],
        #     "type": "memory", # "message" or "memory"
        #     "content": msg_doc,
        #     "emotions": emotions,
        #     "id": id,
        #     "conversation_id": metadata["conversation_id"],
        # }
        # print(msg)
        msg_dict = {
            "role": msg[3],
            "timestamp": msg[4],
            "location": msg[5],
            "type": msg[6],
            "content": msg[2],
            "id": msg[0],
            "name": msg[1],
            "emotions": {}
        }
        for emotion, index in zip(me.config.emotion_composition, range(7,7+len(me.config.emotion_composition))):
            msg_dict["emotions"][emotion] = msg[index]
        msg_dict["conversation_id"] = msg[-1]
        msgs.append(msg_dict)
    print(len(msgs),"messages to save")
    print(msgs[0])
    for msg in msgs:
        # How the original memories are added:
        # memory_metadata = {
        #     "role": message["role"],
        #     "timestamp": message["timestamp"],
        #     "location": message["location"],
        #     "conversation_id": self.conversation_manager.conversation_id,
        # }
        # if "type" not in message:
        #     message["type"] = "message"
        # if 'name' in message:
        #     memory_metadata['name'] = message['name']
        # if self.last_message is not None and "conversation_id" in self.last_message:
        #     if message["conversation_id"] == self.last_message["conversation_id"]:
        #         memory_metadata["last_message_id"] = self.last_message["id"]
        # for emotion in emotion_data:
        #     memory_metadata[emotion] = float(emotion_data[emotion])
        #     if self.config.empathy or message["role"] == self.name: # if empathy is enabled or the message is from the bot
        #         self.emotional_state[emotion] += emotion_data[emotion]
        # self.messages_memories.add(documents=[message["content"]], metadatas=[memory_metadata], ids=[message["id"]])
        messages_memories.update(ids=[msg["id"]],documents=[msg["content"]],metadatas=[{
            "role": msg["role"],
            "timestamp": msg["timestamp"],
            "location": msg["location"],
            "conversation_id": msg["conversation_id"],
            "name": msg["name"],
            **msg["emotions"]
        }])
    return "Saved Memories"
