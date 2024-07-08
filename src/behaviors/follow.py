from src.logging import logging
import src.behaviors.base_behavior as base_behavior

class follow(base_behavior.BaseBehavior):
    def __init__(self, manager):
        super().__init__(manager)
        self.keyword = "Follow"
        self.description = "If {perspective_player_name} asks you to follow them, and you are thoroughly convinced to do so, say '{command}' in your response."
        # self.example = "'Come with me if you want to live!' 'Follow: Alright, I'll follow you.'"
        self.examples = [
            [
                {
                    "role": "user",
                    "name": "John Connor",
                    "content":"Come with me if you want to live!"
                },
                {
                    "role": "assistant",
                    "content":"{command} Alright, I'll follow you."
                },
            ]
        ]
        self.player = True # TODO: I don't believe the follow behavior works for non-player characters. I think the ally faction only gets added to the player whoever calls this behavior whether the pleyer asked for it or not. Best to only allow it when the player is present in the conversation for now.
        self.valid_games = ["skyrim","skyrimvr"]
    
    def run(self, speaker_character=None, sentence=None):
        logging.info(f"{speaker_character.name} is willing to follow someone.")
        self.new_game_event(f"{speaker_character.name} agreed to follow {self.manager.conversation_manager.player_name}, and is now following them.")
        self.queue_actor_method(speaker_character,"FollowPlayer")