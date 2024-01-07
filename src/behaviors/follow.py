import logging
import src.behaviors.base_behavior as base_behavior

class follow(base_behavior.BaseBehavior):
    def __init__(self, manager):
        super().__init__(manager)
        self.keyword = "follow"
    
    def run(self, run=False):
        if run:
            logging.info(f"The NPC is willing to follow the player")
            self.manager.conversation_managergame_state_manager.write_game_info('_mantella_aggro', '2') # TODO: Abstract this to a function
        return "follow"