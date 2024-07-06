print("Loading chromadb_memory.py...")
from src.logging import logging
import os
import json
import chromadb
from chromadb.config import Settings
from src.memory_managers.base_memory_manager import base_MemoryManager
from src.torchmoji.sentence_tokenizer import SentenceTokenizer
from src.torchmoji.model_def import torchmoji_emojis, torch
import numpy as np
logging.info("Imported required libraries in chromadb_memory.py")

def top_elements(array, k):
    ind = np.argpartition(array, -k)[-k:]
    return ind[np.argsort(array[ind])][::-1]

manager_slug = "chromadb_memory"

class MemoryManager(base_MemoryManager):
    def __init__(self,conversation_manager):
        super().__init__(conversation_manager)
        logging.info("Loading ChromaDB Memory Manager")
        self.memory_update_interval = self.config.memory_update_interval
        self.memory_update_interval_counter = 0
        if not os.path.exists(self.conversation_history_directory):
            os.makedirs(self.conversation_history_directory)
        if not os.path.exists(self.conversation_history_directory+"chromadb/"):
            os.makedirs(self.conversation_history_directory+"chromadb/")
        self.client = chromadb.PersistentClient(self.conversation_history_directory+"chromadb/",Settings(anonymized_telemetry=False))
        
        logging.info("Loading TorchMoji...")
        if self.config.linux_mode:
            torchmoji_model_path = os.path.join(os.getcwd(), "data/models/torchmoji/pytorch_model.bin")
            torchmoji_vocab_path = os.path.join(os.getcwd(), "data/models/torchmoji/vocabulary.json")
            emoji_codes_path = os.path.join(os.getcwd(), "data/models/torchmoji/emoji_codes.json")
        else:
            torchmoji_model_path = os.path.join(os.getcwd(), "data\\models\\torchmoji\\pytorch_model.bin")
            torchmoji_vocab_path = os.path.join(os.getcwd(), "data\\models\\torchmoji\\vocabulary.json")
            emoji_codes_path = os.path.join(os.getcwd(), "data\\models\\torchmoji\\emoji_codes.json")
        with open(torchmoji_vocab_path, 'r') as f:
            vocabulary = json.load(f)
        
        self.torchmoji_model = torchmoji_emojis(torchmoji_model_path)
        self.torchmoji_tokenizer = SentenceTokenizer(vocabulary, self.config.torchmoji_max_length)
        self.emoji_codes = []
        with open(emoji_codes_path, 'r') as f:
            self.emoji_codes = json.load(f)
        logging.info("TorchMoji loaded.")
        
        logging.info(self.torchmoji_model)
        self.messages_memories = self.client.get_or_create_collection(name="messages")
        # self.memory_blocks = self.client.get_or_create_collection(name="memories")
        self.current_memories = []
        self.logical_memories = ""
        self.emotional_memories = ""
        self.emotional_state = {}
        self.neutral_emotions()
        self.load_messages()
        if len(self.get_all_messages()) > 0:
            self.update_memories()
            
    def load_messages(self):
        """Load messages from the memory manager - Some memory managers may need to load messages from a file or database, and can also use this method to load old messages into the conversation_manager's messages"""
        if len(self.conversation_manager.messages) == 0:
            reload_buffer_messages = self.get_all_messages()[-self.config.reload_buffer:] # Load the last n messages into the conversation manager
            for message in reload_buffer_messages:
                message["type"] = "memory"
                self.conversation_manager.new_message(message)
        else:
            new_messages = self.get_all_messages()[-self.config.reload_buffer:]
            for message in new_messages:
                if not self.conversation_manager.has_message(message):
                    self.conversation_manager.messages.append(message)
        if len(self.conversation_manager.messages) == 0: # TODO: Find a way to remove this, but this should help models not knowing how to reply as the chaaracter a bit.
            self.conversation_manager.new_message({
                "role": self.config.system_name,
                "content": "Hello! I am "+self.name+".",
                "type": "starting_message"
            })

    def next_emotional_decay(self):
        """Get the next emotional decay value"""
        return np.random.uniform(self.config.emotional_decay_min, self.config.emotional_decay_max)
        
    def predict(self, string, emoji_count=10):
        """Predict emojis from a string"""
        if string.strip() == '':
            # dotted face emoji
            return {"🫥":1}

        return_label = {}
        # tokenize input text
        tokenized, _, _ = self.torchmoji_tokenizer.tokenize_sentences([string])

        if len(tokenized) == 0:
            # dotted face emoji
            return {"🫥":1}
        
        # print(tokenized,type(tokenized))

        prob = self.torchmoji_model(tokenized)

        for prob in [prob]:
            # Find top emojis for each sentence. Emoji ids (0-63)
            # correspond to the mapping in emoji_overview.png
            # at the root of the torchMoji repo.
            for i, t in enumerate([string]):
                t_prob = prob[i]
                # sort top
                ind_top_ids = top_elements(t_prob, emoji_count)

                for ind in ind_top_ids:
                    # unicode emoji + :alias:
                    label_name = self.emoji_codes[str(ind)]
                    # propability
                    label_prob = t_prob[ind]
                    return_label[label_name] = label_prob

        if len(return_label) == 0:
            # dotted face emoji
            return {"🫥":1}

        return return_label

    def before_step(self):
        """Perform a step in the memory manager - Some memory managers may need to perform some action every step"""
        self.memory_update_interval_counter += 1
        if self.memory_update_interval_counter >= self.memory_update_interval:
            self.memory_update_interval_counter = 0
            self.update_memories()

    @property
    def query(self):
        """Return the query string for the memory manager using the self.config.query_size"""
        query_string = ""
        for i in range(self.config.chromedb_query_size):
            if i < len(self.conversation_manager.messages):
                query_string += self.conversation_manager.messages[-1-i]["content"] + "\n"
            else:
                break
        return query_string

    def update_memories(self):
        """Update the memories stored in the memory manager - Some memory managers may need to update memories every step"""
        if len(self.conversation_manager.messages) == 0:
            return
        self.current_memories = self.get_most_related_memories(self.query,self.config.logical_memories,self.config.chromadb_memory_messages_before,self.config.chromadb_memory_messages_after)
    
    def reached_conversation_limit(self):
        """Ran when the conversation limit is reached, or the conversation is ended - Some memory managers may need to perform some action when the conversation limit is reached"""
        logging.info("Conversation limit reached, nothing to do in ChromaDB Memory Manager.")
    
    def add_message(self, message):
        """Add a message to the memory manager - ChromaDB keeps a log of all messages in a jsonl file"""
        logging.info(f"Adding message to ChromaDB: {message}")
        emotion_data = self.get_emotions(message["content"])
        memory_metadata = {
            "role": message["role"],
            "timestamp": message["timestamp"],
            "location": message["location"],
            "conversation_id": self.conversation_manager.conversation_id,
        }
        if "type" not in message:
            message["type"] = "message"
        if 'name' in message:
            memory_metadata['name'] = message['name']
        if self.last_message is not None and "conversation_id" in self.last_message:
            if message["conversation_id"] == self.last_message["conversation_id"]:
                memory_metadata["last_message_id"] = self.last_message["id"]
        for emotion in emotion_data:
            memory_metadata[emotion] = float(emotion_data[emotion])
            if self.config.empathy or message["role"] == self.name: # if empathy is enabled or the message is from the bot
                self.emotional_state[emotion] += emotion_data[emotion]
        self.messages_memories.add(documents=[message["content"]], metadatas=[memory_metadata], ids=[message["id"]])
        # test_memory = self.get_most_related_memories(message["content"],self.config.logical_memories,self.config.chromadb_memory_messages_before,self.config.chromadb_memory_messages_after)
        # logging.info(f"Most Related Memories:", json.dumps(test_memory, indent=2))
        logging.info(f"Added message to ChromaDB: {message}")

    @property
    def emotion_composition(self):
        """User customizable object that is used to store which emojis form which emotions - This is used to determine the emotional state of the bot"""
        return self.config.emotion_composition
    
    def get_emotions(self, string):
        """Get the emotions of a string"""
        emotions = self.format_prediction(self.predict(string, 64))
        logging.info(f"String: {string}")
        logging.info(f"Emotions:", json.dumps(emotions, indent=2))
        return emotions

    def neutral_emotions(self):
        """Set the emotional state of the bot to neutral"""
        for emotion in self.emotion_composition:
            self.emotional_state[emotion] = 0.0

    def format_prediction(self, prediction):
        """Format the prediction from the TorchMoji model into the composed emotions"""
        logging.info(f"Prediction:",prediction)
        composed_emotions = {}
        for emotion in self.emotion_composition:
            composed_emotions[emotion] = 0.0
            emojis = 0
            for emoji in self.emotion_composition[emotion]:
                if ":"+emoji+":" in prediction:
                    composed_emotions[emotion] += prediction[":"+emoji+":"]
                    emojis += 1
            if emojis > 0:
                composed_emotions[emotion] /= emojis
        return composed_emotions

    def get_related_messages(self, query_string, n_results=10):
        """Get the most related messages to a query string from the memory of this character"""
        message_query = self.messages_memories.query(
            query_texts=query_string,
            n_results=n_results,
            where={
                "role": {
                    "$ne": self.config.system_name
                }
            }
        )
        print(message_query)
        msgs = []
        for i in range(len(message_query["documents"][0])):
            msg_doc = message_query["documents"][0][i]
            metadata = message_query["metadatas"][0][i]
            distance = message_query["distances"][0][i]
            if distance == 0.0:
                continue
            id = message_query["ids"][0][i]
            emotions = {}
            for emotion in self.emotion_composition:
                if emotion in metadata:
                    emotions[emotion] = metadata[emotion]
            score = 100.0 - distance
            score = score / 100.0
            msg = {
                "role": metadata["role"],
                "timestamp": metadata["timestamp"],
                "location": metadata["location"],
                "type": "memory", # "message" or "memory"
                "distance": distance,
                "score": score,
                "content": msg_doc,
                "emotions": emotions,
                "id": id,
            }
            if "name" in metadata:
                msg["name"] = metadata["name"]
            msgs.append(msg)
        return msgs
    
    def get_most_related_memories(self, query_string, n_results=1, messages_before=2, messages_after=2):
        """Get the most related memories to a query string from the memory of this character"""
        logging.info(f"Getting most related memories to query string:", query_string)
        msgs = self.get_related_messages(query_string, n_results)
        memories = []
        for msg in msgs:
            memory = self.get_around_message(msg, messages_before, messages_after)
            memories.append(memory)
        # Go through each memory, and if there are overlapping memories, combine them in the correct order without duplicate messages
        combined_memories = []
        for memory in memories:
            for message in memory:
                if message not in combined_memories:
                    combined_memories.append(message)
        # Ensure there are no duplicate messages
        unique_ids = set(list(map(lambda x: x["id"], combined_memories)))
        unique_memories = []
        for message in combined_memories:
            if message["id"] in unique_ids:
                unique_memories.append(message)
                unique_ids.remove(message["id"])
        # ensure there are no messages from system that say the same thing
        # sort by timestamp
        unique_memories = sorted(unique_memories, key=lambda x: x["timestamp"])
        logging.info(f"Unique Memories:", json.dumps(unique_memories, indent=2))
        return unique_memories
    
    def get_all_messages(self):
        """Get all messages in the memory of this character"""
        messages = self.messages_memories.get()
        print("All Messages:",json.dumps(messages, indent=2))
        msgs = []
        for i in range(len(messages["documents"])):
            msg_doc = messages["documents"][i]
            metadata = messages["metadatas"][i]
            id = messages["ids"][i]
            emotions = {}
            for emotion in self.emotion_composition:
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
            msgs.append(msg)
        return msgs

    def get_message_index(self, message):
        """Get the index of a message"""
        messages = self.get_all_messages()
        for i in range(len(messages)):
            if messages[i]["id"] == message["id"]:
                return i # Message found
        return -1 # Message not found

    def get_around_message(self, message, messages_before=2, messages_after=2):
        """Get the messages around a message"""
        logging.info(f"Getting messages around message:", json.dumps(message, indent=2))
        message_index = self.get_message_index(message)
        messages = self.get_all_messages()
        if message_index == -1:
            logging.error("Message not found in memory, cannot get messages around it.")
            return []
        around_messages = []
        for i in range(message_index-messages_before, message_index+messages_after+1):
            if i >= 0 and i < len(messages):
                around_messages.append(messages[i])
        # sort by timestamp
        around_messages = sorted(around_messages, key=lambda x: x["timestamp"])
        return around_messages

    @property
    def memories(self):
        """Return the current memories of the character"""
        mem_messages = [{
            "role": self.config.system_name,
            "content": "The following messages are examples of how behaviors work. Behaviors are how the assistant can do actions in the game world. If an asterisk roleplay coincides with a behavior the assistant should use the behavior to facilitate the asterisk roleplay in the game world. Here are the the examples of how behaviors work:",
            "type": "prompt"
        }]
        behavior_memories = self.conversation_manager.behavior_manager.get_behavior_memories(self.character_manager)
        for memory in behavior_memories:
            mem_messages.append(memory)
        if len(self.current_memories) == 0:
            return mem_messages
        mem_messages.append({
            "role": self.config.system_name,
            "content": self.name+" is thinking about the following memories:",
            "type": "prompt"
        })
        for memory in self.current_memories:
            if memory["role"] != self.config.system_name:
                mem_messages.append(memory)
        return mem_messages

    @property
    def memory_offset(self):
        """Return the memory depth of the character"""
        return self.config.chromadb_memory_depth
    
    @property
    def memory_offset_direction(self):
        """Return the memory offset direction of the character"""
        return self.config.chromadb_memory_direction
    
    @property
    def last_message(self):
        """Return the last message of the character"""
        return self.conversation_manager.messages[-1]