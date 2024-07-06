print("Loading character_manager.py")
from src.logging import logging
import os
import src.memory_manager as mm
import json
import random
logging.info("Imported required libraries in character_manager.py")

class Character:
    def __init__(self, characters_manager, info, is_generic_npc):
        self.characters_manager = characters_manager
        self.info = info
        logging.info(self.info)
        logging.info(f"Loading character: {self.info['name']}")
        logging.info(json.dumps(info, indent=4))
        for key, value in info.items():
            setattr(self, key, value) # set all character info as attributes of the character object to support arbitrary character info
        if "knows" not in self.info:
            self.knows = []
        else:
            if type(self.info["knows"]) == str:
                self.knows = self.info["knows"].split(",")
            elif type(self.info["knows"]) == list:
                self.knows = self.info["knows"]
            else:
                self.knows = []
        self.memory_manager = mm.create_manager(self) # create memory manager for the character
        self.stranger = True
        if len(self.memory_manager.get_all_messages()) > 0:
            self.stranger = False
        self.load_knows()
        # Legend for a few of the more important attributes:
        # self.ref_id - The reference ID of the character as hex with the first two numbers(the load order ID) removed - This is the id of the character in the game, so it is unique to each every single character in the game.
        # self.base_id - The base ID of the character as hex with the first two numbers(the load order ID) removed - This is the id of the character in the editor, so it is unique to each character type (e.g. all bandits have the same baseid, but all one of a single unique character has the same baseid as well)
        if "lang_override" in self.info and self.info["lang_override"] != None and str(self.info["lang_override"]).strip() != "" and str(self.info["lang_override"]).strip() != "nan": # If the character has a language override, use it
            logging.info(f"Language override found for {self.name}: {self.info['lang_override']}")
            self.language_code = self.info["lang_override"]
        else: # If the character does not have a language override, use the player's language
            self.language_code = self.conversation_manager.language_info['alpha2']
        self.language = self.conversation_manager.language_info['language']
        self.is_generic_npc = is_generic_npc
        if "in_game_relationship_level" not in self.info:
            self.in_game_relationship_level = 0
        self.check_for_new_knows(self.bio, False)

        if "age" not in self.info:
            self.age = "Adult" # default age - This is to help communicate to the AI the age of the actor they're playing to help them stay in character
            if "Old" in self.voice_model:
                self.age = "Old"
            elif "Young" in self.voice_model:
                self.age = "Young Adult"
            elif "Child" in self.voice_model:
                self.age = "Child"
            elif "Teen" in self.voice_model:
                self.age = "Teen"
        self.gendered_age = "" # default gendered age - This is also to help communicate to the AI the age of the actor they're playing to help them stay in character
        if self.gender == "Male":
            if self.age == "Child" or self.age == "Teen":
                self.gendered_age = "Boy"
            elif self.age == "Old":
                self.gendered_age = "Old Man"
            else:
                self.gendered_age = "Man"
        else:
            if self.age == "Child" or self.age == "Teen":
                self.gendered_age = "Girl"
            elif self.age == "Old":
                self.gendered_age = "Old Lady"
            else:
                self.gendered_age = "Woman"
        self.save_knows()

    def save_knows(self):
        if not os.path.exists(self.memory_manager.conversation_history_directory):
            os.makedirs(self.memory_manager.conversation_history_directory, exist_ok=True)
        if not os.path.exists(self.memory_manager.conversation_history_directory+"knows"):
            with open(self.memory_manager.conversation_history_directory+"knows", 'w', encoding='utf-8') as f:
                f.write("")
        current_knows = ""
        with open(self.memory_manager.conversation_history_directory+"knows", 'r', encoding='utf-8') as f:
            current_knows = f.read()
        current_knows = current_knows.split(",")
        for know in self.knows:
            if know not in current_knows:
                with open(self.memory_manager.conversation_history_directory+"knows", 'a', encoding='utf-8') as f:
                    f.write(know+",")

    def load_knows(self):
        if not os.path.exists(self.memory_manager.conversation_history_directory):
            os.makedirs(self.memory_manager.conversation_history_directory, exist_ok=True)
        if not os.path.exists(self.memory_manager.conversation_history_directory+"knows"):
            with open(self.memory_manager.conversation_history_directory+"knows", 'w', encoding='utf-8') as f:
                f.write("")
        with open(self.memory_manager.conversation_history_directory+"knows", 'r', encoding='utf-8') as f:
            new_knows = f.read()
            new_knows = new_knows.split(",")
            total_unique_knows = set(self.knows + new_knows)
            self.knows = list(total_unique_knows)

    def meet(self, other_character_name, add_game_events=True):
        if other_character_name not in self.knows:
            meet_string = f"{self.name} remembered {other_character_name}'s name."
            logging.info(meet_string)
            if add_game_events:
                with open(f'{self.conversation_manager.config.game_path}/_pantella_in_game_events.txt', 'a') as f:
                    f.write(meet_string + '\n')
            self.knows.append(other_character_name)
            self.knows = list(set(self.knows))
            self.save_knows()

    @property
    def conversation_manager(self):
        return self.characters_manager.conversation_manager
    
    @property
    def config(self):
        return self.conversation_manager.config
    
    def get_perspective_identity(self, name, race, gender, relationship_level):
        # The highest relationship rank this actor has.

        # The following values are returned and are intended to mean in game as follows:

        #     4: Lover
        #     3: Ally
        #     2: Confidant
        #     1: Friend
        #     0: Acquaintance
        #     -1: Rival
        #     -2: Foe
        #     -3: Enemy
        #     -4: Archnemesis
        trust = 'stranger'
        perspective_name = "A stranger" # Who the character thinks the player is
        if not self.stranger:
            if relationship_level == -4:
                trust = 'Archnemesis'
                perspective_name = f"{self.name}'s {race} {gender} archnemesis"
            elif relationship_level == -3:
                trust = 'Enemy'
                perspective_name = f"{self.name}'s {race} {gender} enemy"
            elif relationship_level == -2:
                trust = 'Foe'
                perspective_name = f"{self.name}'s {race} {gender} foe"
            elif relationship_level == -1:
                trust = 'Rival'
                perspective_name = f"{self.name}'s {race} {gender} rival"
            elif relationship_level == 0:
                trust = 'Acquaintance'
                perspective_name = f"{race} {gender} Acquaintance of {self.name}"
            elif relationship_level == 1:
                trust = 'Friend'
                perspective_name = f"{self.name}'s mysterious {race} {gender} friend"
            elif relationship_level == 2:
                trust = 'Confidant'
                perspective_name = f"{self.name}'s mysterious {race} {gender} confidant"
            elif relationship_level == 3:
                trust = 'Ally'
                perspective_name = f"{self.name}'s mysterious {race} {gender} ally"
            elif relationship_level == 4:
                trust = 'Lover'
                perspective_name = f"{self.name}'s mysterious {race} {gender} lover"
        else:
            trust = 'Stranger'
            perspective_name = f"{race} {gender} Stranger"
        if name in self.knows: # If the character knows the player's name, use it
            perspective_name = f"{name} {race} {gender} {trust} of {self.name}"

        return perspective_name, trust
    
    def get_perspective_player_identity(self):
        return self.get_perspective_identity(self.characters_manager.conversation_manager.player_name, self.characters_manager.conversation_manager.player_race, self.characters_manager.conversation_manager.player_gender, self.in_game_relationship_level)

    @property
    def replacement_dict(self):
        perspective_name, trust = self.get_perspective_player_identity()
        try:
            with open(self.conversation_summary_file, 'r', encoding='utf-8') as f:
                previous_conversation_summaries = f.read()
        except:
            previous_conversation_summaries = ''

        self.conversation_summary = previous_conversation_summaries
        return {
            "name": self.name,
            "race": self.race,
            "gender": self.gender,
            "age": self.age,
            "gendered_age": self.gendered_age,
            "perspective_player_name": perspective_name,
            "bio": self.bio,
            "trust": trust,
            "language": self.language,
        }
    
    @property
    def memories(self):
        return self.memory_manager.memories

    def say(self,string, remember=True):
        audio_file = self.conversation_manager.synthesizer.synthesize(string, self) # say string
        self.conversation_manager.game_interface.save_files_to_voice_folders([audio_file, string]) # save audio file to voice folder so it can be played in-game
        if remember:
            self.conversation_manager.new_message({"role": self.config.assistant_name, "name":self.name, "content": string}) # add string to ongoing conversation

    def leave_conversation(self):
        random_goodbye = random.choice(self.conversation_manager.config.goodbye_npc_responses) # get random goodbye line from player
        if random_goodbye.endswith('.'):
            random_goodbye = random_goodbye[:-1]
        self.say(random_goodbye+'.',False) # let the player know that the conversation is ending using the latest character in the conversation that isn't the player to say it
        self.reached_conversation_limit()

    def after_step(self):
        """Perform a step in the memory manager - Some memory managers may need to perform some action every step"""
        self.memory_manager.after_step()
        
    def before_step(self):
        """Perform a step in the memory manager - Some memory managers may need to perform some action every step"""
        self.memory_manager.before_step()

    def reached_conversation_limit(self):
        """Ran when the conversation limit is reached, or the conversation is ended - Some memory managers may need to perform some action when the conversation limit is reached"""
        return self.memory_manager.reached_conversation_limit()
    
    def add_message(self, msg):
        """Add a new message to the memory manager"""
        if msg["role"] != self.config.system_name:
            self.check_for_new_knows(msg["content"])
            self.memory_manager.add_message(msg)

    def check_for_new_knows(self, msg, add_game_events=True):
        """Check if the message contains a new character that the character has met"""
        valid_names = [character["name"] for character in self.conversation_manager.character_database.characters]
        valid_names.append(self.conversation_manager.player_name)
        valid_names = [name for name in valid_names if name != None]
        valid_names = [name for name in valid_names if name not in self.config.banned_learnable_names]
        lower_case_versions = [name.lower() for name in valid_names]
        pairs = list(zip(valid_names, lower_case_versions))
        msg_words = msg.split(" ")
        for name, lower_case_name in pairs:
            if lower_case_name in msg_words:
                self.meet(name, add_game_events)

    def __str__(self):
        return self.name + " (" + self.race + " " + self.gender + ")"