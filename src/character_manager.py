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
        logging.config(json.dumps(info, indent=4))
        for key, value in info.items():
            if key != "age" and key != "gender" and key != "race":
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
        # if "language_override" in self.info and self.info["language_override"] != None and str(self.info["language_override"]).strip() != "" and str(self.info["language_override"]).strip() != "nan": # If the character has a language override, use it
        #     logging.info(f"Language override found for {self.name}: {self.info['language_override']}")
        #     self.language_code = self.info["language_override"]
        # else: # If the character does not have a language override, use the default language
        #     self.language_code = self.config.default_language
        # self.language = self.config.languages[self.language_code]
        self.is_generic_npc = is_generic_npc
        if "in_game_relationship_level" not in self.info:
            self.in_game_relationship_level = 0
        self.check_for_new_knows(self.bio, False)
        self.save_knows()
        
    @property
    def age(self):
        age = "adult" # default age - This is to help communicate to the AI the age of the actor they're playing to help them stay in character
        if "age" not in self.info or (("age" in self.info and self.info["age"] == None) or ("age" in self.info and self.info["age"] == "")):
            if "Old" in self.voice_model:
                age = "old"
            elif "Young" in self.voice_model:
                age = "young_adult"
            elif "Child" in self.voice_model:
                age = "child"
            elif "Teen" in self.voice_model:
                age = "teen"
        else:
            age = self.info["age"]
        return age
    
    @property
    def race(self):
        race = "Imperial"
        if "race" in self.info and self.info["race"] != None and self.info["race"] != "":
            race = self.info["race"]
        elif "in_game_race" in self.info and self.info["in_game_race"] != None and self.info["in_game_race"] != "":
            race = self.info["in_game_race"]
        # if race.lower().capitalize() in self.language["race_titles"]: # Infinte recursion error with language property
        #     race = self.language["race_titles"][race.lower().capitalize()]
        return race
    
    @property
    def gender(self):
        gender = "Imperial"
        if "gender" in self.info and self.info["gender"] != None and self.info["gender"] != "":
            gender = self.info["gender"]
        elif "in_game_gender" in self.info and self.info["in_game_gender"] != None and self.info["in_game_gender"] != "":
            gender = self.info["in_game_gender"]
        if gender.lower().capitalize() in self.language["race_titles"]:
            if self.race in self.prompt_style["racial_language"]:
                logging.info(f"Racial language found for {self.name}: {gender}")
                gender = self.language["racial_language"][self.race]["gender_title"][gender.lower().capitalize()]
            else:
                gender = self.language["gender_titles"][gender.lower().capitalize()]
        return gender
    
    @property
    def age_title(self):
        return self.language["race_titles"][self.race]
    
    @property
    def age_title(self):
        return self.language["age_titles"][self.age]
    
    @property
    def gendered_age(self):
        return self.language["aged_gendered_titles"][self.gender][self.age]

    @property
    def _prompt_style(self):
        if self.prompt_style_override.strip() != "":
            # logging.info(f"Prompt style override found for {self.name}: {self.prompt_style_override}")
            return self.characters_manager.conversation_manager.config.prompt_styles[self.prompt_style_override]
        # logging.info(f"No prompt style override found for {self.name}, using default prompt style settings for {self.config.prompt_style}")
        return self.characters_manager.conversation_manager.config._prompt_style
    @property
    def prompt_style(self):
        return self._prompt_style["style"]
    
    @property
    def language(self):
        if self.race in self._prompt_style["racial_language"]: # If the character has a racial language, use the default as a template and override anything different with the racial language over the default
            language = self._prompt_style["language"]
            logging.info(f"Racial language found for {self.name}:",language)
            for key, value in self._prompt_style["racial_language"][self.race].items():
                if key in self.info and self.info[key] == value:
                    language = self._prompt_style["racial_language"][self.race][key]
            return language
        # logging.info(f"No racial language found for {self.name}, using default language settings for '{self._prompt_style['language']['language_code']}'.")
        return self._prompt_style["language"]
    
    @property
    def language_code(self):
        return self.language["language_code"]
    
    @property
    def tts_language_code(self):
        if "tts_language_override" in self.info and self.info["tts_language_override"] != None and str(self.info["tts_language_override"]).strip() != "" and str(self.info["tts_language_override"]).strip() != "nan": # If the character has a language override, use it
            logging.info(f"Language override found for {self.name}: {self.info['tts_language_override']}")
            return self.info["tts_language_override"]
        else: # If the character does not have a tts language override, use the default language
            return self.language["tts_language_code"]

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
            meet_string = self.language["meet_string"].replace("{self_name}", self.name).replace("{other_name}", other_character_name)
            logging.info(meet_string)
            if add_game_events and self.config.meet_string_game_events:
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
    
    def get_perspective_identity(self, name, race, gender, relationship_level=0):
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
        knows = False
        if not self.stranger:
            if relationship_level == -4:
                trust = 'archnemesis'
            elif relationship_level == -3:
                trust = 'enemy'
            elif relationship_level == -2:
                trust = 'foe'
            elif relationship_level == -1:
                trust = 'rival'
            elif relationship_level == 0:
                trust = 'acquaintance'
            elif relationship_level == 1:
                trust = 'friend'
            elif relationship_level == 2:
                trust = 'confidant'
            elif relationship_level == 3:
                trust = 'ally'
            elif relationship_level == 4:
                trust = 'lover'
        if name in self.knows: # If the character knows the player's name, use it
            knows = True
        if knows:
            perspective_name = self.language["known_perspective_name"][trust]
        else:
            perspective_name = self.language["unknown_perspective_name"][trust]
        trust_title = self.language["trust_titles"][trust]
        perspective_name = perspective_name.replace("{self_name}", self.name)
        perspective_name = perspective_name.replace("{other_name}", name)
        perspective_name = perspective_name.replace("{other_race}", race)
        perspective_name = perspective_name.replace("{other_gender}", gender)
        perspective_name = perspective_name.replace("{trust_title}", trust_title)
        return perspective_name, trust
    
    def get_perspective_player_identity(self):
        return self.get_perspective_identity(self.characters_manager.conversation_manager.player_name, self.characters_manager.conversation_manager.player_race, self.characters_manager.conversation_manager.player_gender, relationship_level=self.in_game_relationship_level)

    def update_game_state(self):
        logging.info("Implement: Character.update_game_state() for single player conversations. (character_manager.py: update_game_state()")
        pass

    @property
    def replacement_dict(self):
        perspective_name, trust = self.get_perspective_player_identity()
        return {
            "name": self.name,
            "race": self.race,
            "gender": self.gender,
            "age": self.age,
            "age_title": self.age_title,
            "gendered_age": self.gendered_age,
            "perspective_player_name": perspective_name,
            "trust": trust,
            "bio": self.bio,
            "language": self.language["in_game_language_name"],
            "real_language": self.language["language_name"]
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
        random_goodbye = random.choice(self.language['goodbye_npc_responses']) # get random goodbye line from player
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
        valid_names = [name for name in valid_names if name not in self.language["banned_learnable_names"]]
        lower_case_versions = [name.lower() for name in valid_names]
        pairs = list(zip(valid_names, lower_case_versions))
        msg_words = msg.split(" ")
        for char in self.prompt_style["end_of_sentence_chars"] + [",", ":", ";"]:
            msg_words = [word.replace(char, "") for word in msg_words]
        for name, lower_case_name in pairs:
            if name in msg_words or lower_case_name in msg_words:
                self.meet(name, add_game_events)

    def __str__(self):
        return self.name + " (" + self.race + " " + self.gender + ")"