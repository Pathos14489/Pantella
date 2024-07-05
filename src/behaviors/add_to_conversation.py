from src.logging import logging
import src.behaviors.base_behavior as base_behavior

class add_to_conversation(base_behavior.BaseBehavior):
    def __init__(self, manager):
        super().__init__(manager)
        self.keyword = "AddToConversation"
        self.description = "If you want to talk to {perspective_player_name}, you can use this behavior to add them to the conversation."
        # self.example = "'Do you want coffee?' 'AddToConversation: I'm not sure, me and {player_name} are in the middle of something. {player_name}, do you want coffee?'"
        self.examples = [
            [
                {
                    "role": "user",
                    "name": "Alice",
                    "text": "Do you want coffee?"
                },
                {
                    "role": "assistant",
                    "text": "I'm not sure, me and {player_name} are in the middle of something. {command} {player_name}, do you want coffee?"
                }
            ]
        ]
        self.radiant_only = True
        self.valid_games = ["skyrim","skyrimvr"]
    
    def run(self, speaker_character=None, sentence=None):
        logging.info(f"{speaker_character['name']} is adding {self.manager.conversation_manager.player_name} to the conversation.")
        self.new_game_event(f"{speaker_character['name']} added {self.manager.conversation_manager.player_name} to the conversation.")
        self.queue_actor_method(speaker_character,"AddPlayerToConversation")