import logging
import src.behaviors.base_behavior as base_behavior

class Follow(base_behavior.BaseBehavior):
    def __init__(self, manager):
        super().__init__(manager)
        self.keyword = "follow"
    
    def run(self):
        logging.info(f"The player offended the NPC")
        self.manager.conversation_manager.game_state_manager.write_game_info('_mantella_aggro', '1')
        logging.info(f"The NPC is willing to follow the player")
        self.manager.conversation_managergame_state_manager.write_game_info('_mantella_aggro', '2') # TODO: Abstract this to a function