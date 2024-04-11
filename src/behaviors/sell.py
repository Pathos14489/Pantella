from src.logging import logging
import src.behaviors.base_behavior as base_behavior

class sell(base_behavior.BaseBehavior):
    def __init__(self, manager):
        super().__init__(manager)
        self.keyword = "Sell"
        self.description = "If {perspective_player_name} wants to buy something from {name}, and {name} wants to sell them something, {name} will begin their the sentence starting the barter interaction with 'Sell:'."
        self.example = "'Hey, can I buy something from you?' 'Sell: Sure, what do you want?', 'I want to buy something.' 'Sell: I have a lot of things to sell, what are you interested in?'"
        self.activation_sentences = [
            "Of course, what kind of items are you looking for?",
            "I have a lot of things to sell, what are you interested in?",
            "I have a lot of items to sell, what are you interested in?",
            "I have a lot of food to sell, what are you interested in?",
            "I'm always looking to sell something.",
            "I'm interested in selling something to you.",
            "I'm looking to sell something.",
        ]
        self.valid_games = ["skyrim","skyrimvr"]
    
    def run(self, speaker_character=None, sentence=None):
        logging.info(f"{speaker_character.name} wants to sell something to the {self.manager.conversation_manager.player_name}.")
        self.queue_actor_method(speaker_character,"Wait","2")
        self.new_game_event(f"{speaker_character.name} began selling something to {self.manager.conversation_manager.player_name}.")
        self.queue_actor_method(speaker_character,"OpenBarterMenu")
