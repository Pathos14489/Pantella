from src.logging import logging
import src.behaviors.base_behavior as base_behavior

class give(base_behavior.BaseBehavior):
    def __init__(self, manager):
        super().__init__(manager)
        self.keyword = "Give"
        self.description = "If {perspective_player_name} wants to take something from you, and you want to give it to them, begin your response with 'Give:'."
        self.example = "'Can you give me that?' 'Give: Sure, here you go.'"
        self.valid_games = ["skyrim","skyrimvr"]
    
    def run(self, speaker_character=None, sentence=None):
        logging.info(f"{speaker_character.name} wants to give an item from the player.")
        self.queue_actor_method(speaker_character,"Wait","2")
        self.new_game_event(f"{speaker_character.name} offered {self.manager.conversation_manager.player_name} to take something from them.")
        self.queue_actor_method(speaker_character,"OpenTakeMenu")
