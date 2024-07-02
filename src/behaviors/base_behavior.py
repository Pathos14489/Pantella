from src.logging import logging

class BaseBehavior():
    def __init__(self, manager):
        self.manager = manager
        self.keyword = None
        self.description = None
        self.example = None
        self.radiant_only = False
        self.non_radiant_only = False
        self.player = False # If this behavior can be triggered by the player
        self.player_only = False # If this behavior can only be triggered by the player
        self.npc = False # If this behavior can only be triggered when only NPCs are present
        self.single_npc_with_npc_only = False
        self.single_npc_with_player_only = False
        self.multi_npc_only = False
        self.npc_pre_keywords = [] # Keywords that the NPC can say that will trigger this behavior before generating the voiceline
        self.npc_post_keywords = [] # Keywords that the NPC can say that will trigger this behavior after generating the voiceline
        self.activation_sentences = [] # Sentences that will trigger this behavior
        self.valid_games = [] # List of game IDs that this behavior is valid for

    @property
    def conversation_manager(self):
        return self.manager.conversation_manager
    
    def _run(self, run=False, speaker_character=None, sentence=None):
        if run:
            if sentence is None:
                logging.error(f"{self.keyword} behavior called with no sentence!")
            else:
                self.run(speaker_character, sentence)
        return self.keyword

    def run(self, speaker_character=None, sentence=None):
        logging.error("BaseBehavior run() called for " + self.__class__.__name__ + f"({self.keyword}.py), this should be overwritten by the child class!")
        return self
    
    def player_run(self, sentence=None):
        logging.error("BaseBehavior player_run() called for " + self.__class__.__name__ + f"({self.keyword}.py), this should be overwritten by the child class!")
        return self
    
    def valid(self):
        if not self.conversation_manager.radiant_dialogue and self.radiant_only:
            return False
        if not self.conversation_manager.radiant_dialogue and self.non_radiant_only:
            return False
        conversation_type = self.conversation_manager.get_conversation_type() # single_npc_with_npc, single_npc_with_player, multi_npc
        if conversation_type == "single_npc_with_npc" and (self.single_npc_with_player_only or self.multi_npc_only or self.player): # If the conversation type is single_npc_with_npc, and the behavior is single_npc_with_player_only, multi_npc_only, or npc_only, return False
            return False
        if conversation_type == "single_npc_with_player" and (self.single_npc_with_npc_only or self.multi_npc_only or self.npc):
            return False
        if conversation_type == "multi_npc" and (self.single_npc_with_npc_only or self.single_npc_with_player_only or (self.npc and self.conversation_manager.radiant_dialogue)):
            return False
        if self.player_only:
            return False
        return True
    
    def queue_actor_method(self, speaker_character, method_name, *args):
        """Queue an arbitrary method to be run on the actor in game via the game interface."""
        return self.manager.conversation_manager.game_interface.queue_actor_method(speaker_character, method_name, *args)
    
    def new_game_event(self, game_event_string):
        with open(f'{self.manager.conversation_manager.config.game_path}/_pantella_in_game_events.txt', 'a') as f:
            f.write(game_event_string + '\n')