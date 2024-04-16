import src.utils as utils
import src.llms.base_llm as base_LLM
import src.tokenizers.base_tokenizer as tokenizer
from src.logging import logging, time

inference_engine_name = "chat_llm"

class base_LLM(base_LLM.base_LLM):
    def __init__(self, conversation_manager):
        global inference_engine_name
        super().__init__(conversation_manager)
        
    def get_context(self):
        """Get the correct set of messages to use with the LLM to generate the next response"""
        system_prompt = self.character_manager.get_system_prompt() # get system prompt
        msgs = [{'role': self.config.system_name, 'content': system_prompt}] # add system prompt to context
        msgs.extend(self.character_manager.get_memories()) # add memories to context
        msgs.extend(self.messages) # add messages to context
        formatted_messages = [] # format messages to be sent to LLM - Replace [player] with player name appropriate for the type of conversation
        for msg in msgs: # Add player name to messages based on the type of conversation
            if msg['role'] == "[player]":
                if self.character_manager.active_character_count() > 1: # if multi NPC conversation use the player's actual name
                    formatted_messages.append({
                        'role': self.config.user_name,
                        'content': self.player_name + ": " + msg['content'],
                    })
                    if "timestamp" in msg:
                        formatted_messages[-1]["timestamp"] = msg["timestamp"]
                    if "location" in msg:
                        formatted_messages[-1]["location"] = msg["location"]
                else: # if single NPC conversation use the NPC's perspective player name
                    perspective_player_name, trust = self.chat_manager.active_character.get_perspective_player_identity()
                    formatted_messages.append({
                        'role': self.config.user_name,
                        'content': perspective_player_name + ": " + msg['content'],
                    })
                    if "timestamp" in msg:
                        formatted_messages[-1]["timestamp"] = msg["timestamp"]
                    if "location" in msg:
                        formatted_messages[-1]["location"] = msg["location"]
            else:
                if msg['role'] == self.config.system_name:
                    formatted_messages.append({
                        'role': msg['role'],
                        'content': msg['content'],
                    })
                    if "timestamp" in msg:
                        formatted_messages[-1]["timestamp"] = msg["timestamp"]
                    if "location" in msg:
                        formatted_messages[-1]["location"] = msg["location"]
                else:
                    formatted_messages.append({
                        'role': self.config.assistant_name,
                        'content': msg['role'] + ": " + msg['content'],
                    })
                    if "timestamp" in msg:
                        formatted_messages[-1]["timestamp"] = msg["timestamp"]
                    if "location" in msg:
                        formatted_messages[-1]["location"] = msg["location"]
        return formatted_messages