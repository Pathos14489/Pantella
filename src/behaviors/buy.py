import logging
import src.behaviors.base_behavior as base_behavior

class buy(base_behavior.BaseBehavior):
    def __init__(self, manager):
        super().__init__(manager)
        self.keyword = "Buy"
        self.description = "If {perspective_player_name} wants to sell something to {name}, and {name} wants to buy something, to start the barter interaction, {name} will begin their sentence with 'Buy:'."
        self.example = "'Hey, can I sell you something?' 'Buy: Sure, what do you have?'"
        self.activation_sentences = [
            "I'm always looking for new things to buy.",
            "I'm interested in buying something from you.",
            "I'm looking to buy something.",
            "Sure, I can take a look at what you have to sell.",
        ]
    
    def run(self, run=False, speaker_character=None, sentence=None):
        if run:
            if sentence is None:
                logging.error(f"Buy behavior called with no sentence!")
            else:
                logging.info(f"{speaker_character.name} wants to buy something from the {self.manager.conversation_manager.player_name}.")
                self.queue_actor_method(speaker_character,"Wait","2")
                self.new_game_event(f"{speaker_character.name} began buying something from {self.manager.conversation_manager.player_name}.")
                self.queue_actor_method(speaker_character,"OpenBarterMenu")
        return "buy"
    