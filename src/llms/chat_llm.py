import src.utils as utils
import src.llms.base_llm as base_LLM
import src.tokenizers.base_tokenizer as tokenizer
from src.logging import logging, time

inference_engine_name = "chat_llm"

class base_LLM(base_LLM.base_LLM):
    def __init__(self, conversation_manager):
        global inference_engine_name
        super().__init__(conversation_manager)
        self.type = "chat"
        
    def get_context(self):
        """Get the correct set of messages to use with the LLM to generate the next response"""
        msgs = self.get_messages()
        formatted_messages = [] # format messages to be sent to LLM - Replace [player] with player name appropriate for the type of conversation
        for msg in msgs: # Add player name to messages based on the type of conversation
            if msg['role'] == "[player]":
                if self.character_manager.active_character_count() > 1: # if multi NPC conversation use the player's actual name
                    formatted_msg = {
                        'role': self.config.user_name,
                        'content': self.player_name + ": " + msg['content'],
                    }
                    if "timestamp" in msg:
                        formatted_msg["timestamp"] = msg["timestamp"]
                    if "location" in msg:
                        formatted_msg["location"] = msg["location"]
                    if "type" in msg:
                        formatted_msg["type"] = msg["type"]
                else: # if single NPC conversation use the NPC's perspective player name
                    perspective_player_name, trust = self.game_interface.active_character.get_perspective_player_identity()
                    formatted_msg = {
                        'role': self.config.user_name,
                        'content': perspective_player_name + ": " + msg['content'],
                    }
                    if "timestamp" in msg:
                        formatted_msg["timestamp"] = msg["timestamp"]
                    if "location" in msg:
                        formatted_msg["location"] = msg["location"]
                    if "type" in msg:
                        formatted_msg["type"] = msg["type"]
            else:
                if msg['role'] == self.config.system_name:
                    formatted_msg = {
                        'role': msg['role'],
                        'content': msg['content'],
                    }
                    if "timestamp" in msg:
                        formatted_msg["timestamp"] = msg["timestamp"]
                    if "location" in msg:
                        formatted_msg["location"] = msg["location"]
                    if "type" in msg:
                        formatted_msg["type"] = msg["type"]
                else:
                    formatted_msg = {
                        'role': self.config.assistant_name,
                        'content': msg['role'] + ": " + msg['content'],
                    }
                    if "timestamp" in msg:
                        formatted_msg["timestamp"] = msg["timestamp"]
                    if "location" in msg:
                        formatted_msg["location"] = msg["location"]
                    if "type" in msg:
                        formatted_msg["type"] = msg["type"]
            formatted_messages.append(formatted_msg)
        return formatted_messages