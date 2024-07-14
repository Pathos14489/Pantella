print("Loading summarizing_memory memory manager...")
from src.memory_managers.base_memory_manager import base_MemoryManager
from src.logging import logging, time
import os
import traceback
logging.info("Imported required libraries in summarizing_memory.py")

manager_slug = "summarizing_memory"

class MemoryManager(base_MemoryManager):
    def __init__(self,conversation_manager):
        super().__init__(conversation_manager)
        logging.info("Loading summarizing memory manager")

    @property
    def latest_conversation_summary_file_path(self):
        """Get latest conversation summary by file name suffix"""

        # TODO: Somehow make this work with multiple characters of the same name, gender and race or even ideally with the same exact character
        # at different points (e.g. different saves = different conversations with the same character and the same player character)
        # Maybe commmunicate the save index to the user and use that to load the correct save somehow?

        if os.path.exists(self.conversation_history_directory):
            # get all files from the directory
            files = os.listdir(self.conversation_history_directory)
            # filter only .txt files
            txt_files = [f for f in files if f.endswith('.txt')]
            if len(txt_files) > 0:
                file_numbers = [int(os.path.splitext(f)[0].split('_')[-1]) for f in txt_files]
                latest_file_number = max(file_numbers)
            else:
                logging.info(f"{self.conversation_history_directory} does not exist. A new summary file will be created.")
                latest_file_number = 1
        else:
            logging.info(f"{self.conversation_history_directory} does not exist. A new summary file will be created.")
            latest_file_number = 1

        
        conversation_summary_file = f"{self.conversation_history_directory}/{self.name}_summary_{latest_file_number}.txt"
        logging.info(f"Loaded latest summary file: {conversation_summary_file}")
        full_absolute_path = os.path.join(os.getcwd(), conversation_summary_file)
        return full_absolute_path
    
    def save_conversation(self, summary=None):
        """Save the conversation history and generate a summary of the conversation history if the token limit is reached."""
        if self.character_manager.is_generic_npc:
            logging.info('A summary will not be saved for this generic NPC.')
            return None
        
        summary_limit = round(self.conversation_manager.tokens_available*self.config.summary_limit_pct,0) # How many tokens the summary can be before it is summarized

        # save conversation history
        
        # if os.path.exists(self.latest_conversation_summary_file_path): # if this is not the first conversation load the previous conversation history from the conversation history file
        #     with open(self.latest_conversation_summary_file_path, 'r', encoding='utf-8') as f:
        #         conversation_history = json.load(f)

        #     # add new conversation to conversation history
        #     conversation_history.append(self.conversation_manager.messages) # append everything except the initial system prompt
        
        # else: # if this is the first conversation initialize the conversation history file and set the previous conversation history to an every message except the initial system prompt
        #     directory = os.path.dirname(self.latest_conversation_summary_file_path)
        #     os.makedirs(directory, exist_ok=True)
        #     conversation_history = [self.conversation_manager.messages]
        
        # with open(self.latest_conversation_summary_file_path, 'w', encoding='utf-8') as f: # save everything except the initial system prompt
        #     json.dump(conversation_history, f, indent=4)

        
        if os.path.exists(self.latest_conversation_summary_file_path): # if this is not the first conversation load the previous conversation summaries from the conversation summary file
            with open(self.latest_conversation_summary_file_path, 'r', encoding='utf-8') as f:
                previous_conversation_summaries = f.read()
        else: # if this is the first conversation, initialize the conversation summary file and set the previous conversation summaries to an empty string
            directory = os.path.dirname(self.latest_conversation_summary_file_path)
            os.makedirs(directory, exist_ok=True)
            previous_conversation_summaries = ''

        # If summary has not already been generated for another character in a multi NPC conversation (multi NPC memory summaries are shared)
        if summary == None:
            while True:
                try:
                    new_conversation_summary = self.summarize_conversation()
                    break
                except Exception as e:
                    logging.error('Failed to summarize conversation...')
                    logging.error(e)
                    tb = traceback.format_exc()
                    logging.error(tb)
                    print(e)
                    input('Press enter to continue...')
                    raise e
        else:
            new_conversation_summary = summary
        conversation_summaries = previous_conversation_summaries + new_conversation_summary

        with open(self.latest_conversation_summary_file_path, 'w', encoding='utf-8') as f:
            f.write(conversation_summaries)

        # if summaries token limit is reached, summarize the summaries
        if self.conversation_manager.tokenizer.get_token_count(conversation_summaries) > summary_limit:
            logging.info(f'Token limit of conversation summaries reached ({len(self.conversation_manager.tokenizer.get_token_count(conversation_summaries))} / {summary_limit} tokens). Creating new summary file...')
            while True:
                try:
                    prompt = self.character_manager.prompt_style["langauge"]["summarizing_memory_prompt"].replace("{self_name}",self.name).replace("{other_name}",self.character_manager.get_perspective_player_identity()[0]).replace("{language}",self.config.language['language']["in_game_language_name"])
                    long_conversation_summary = self.summarize_conversation(prompt)
                    break
                except:
                    logging.error('Failed to summarize conversation. Retrying...')
                    time.sleep(5)
                    continue

            # Split the file path and increment the number by 1
            base_directory, filename = os.path.split(self.latest_conversation_summary_file_path)
            file_prefix, old_number = filename.rsplit('_', 1)
            old_number = os.path.splitext(old_number)[0]
            new_number = int(old_number) + 1
            new_conversation_summary_file = os.path.join(base_directory, f"{file_prefix}_{new_number}.txt")

            with open(new_conversation_summary_file, 'w', encoding='utf-8') as f:
                f.write(long_conversation_summary)
        
        return new_conversation_summary

    def summarize_all_summaries(self):
        """Summarize all summaries in the conversation"""
        summary = None
        for _, character in self.conversation_manager.character_manager.active_characters.items(): # Get conversation summary from any character in the conversation or generate a new one
            if summary == None: # If summary has already been generated for another character in a multi NPC conversation (multi NPC memory summaries are shared)
                summary = character.memory_manager.save_conversation()
            else: # If summary has not been generated yet, generate it
                _ = character.memory_manager.save_conversation(summary)
        return summary

    def summarize_conversation(self, prompt=None):
        """Summarize the conversation history"""
        perspective_name, _ = self.character_manager.get_perspective_player_identity()
        summary = ''
        context = self.conversation_manager.get_context()
        if len(context) > self.conversation_manager.config.min_conversation_length:
            conversation = context[3:-2] # drop the context (0) hello (1,2) and "Goodbye." (-2, -1) lines
            if prompt == None: # If no summarization prompt is provided, use default
                prompt = self.character_manager.prompt_style["langauge"]["summarizing_memory_prompt"].replace("{self_name}",self.name).replace("{other_name}",self.character_manager.get_perspective_player_identity()[0]).replace("{language}",self.config.language['language']["in_game_language_name"])
            context = [{"role": self.conversation_manager.config.system_name, "content": prompt}]
            history = ""
            for message in conversation:
                history += message["role"] + ": " + message["content"] + "\n"
            history = history.strip() # remove trailing newline
            summary, _ = self.conversation_manager.llm.chatgpt_api(history, context) # TODO: Change to use acreate instead of chatgpt_api, I don't think this works with the use of none "system", "user" and "assistant" roles being in the conversation history

            summary = summary.replace('The assistant', self.name)
            summary = summary.replace('the assistant', self.name)
            summary = summary.replace('an assistant', self.name)
            summary = summary.replace('an AI assistant', self.name)
            summary = summary.replace('The user', perspective_name)
            summary = summary.replace('The User', perspective_name)
            summary = summary.replace('the user', perspective_name)
            summary = summary.replace('The player', perspective_name)
            summary = summary.replace('The Player', perspective_name)
            summary = summary.replace('the player', perspective_name)
            summary += '\n\n'

            logging.info(f"Conversation summary generated.")
        else:
            logging.info(f"Conversation summary not created. Conversation too short.")

        return summary
    
    def after_step(self):
        """Perform a step in the memory manager - Some memory managers may need to perform some action every step"""
        pass
    
    def before_step(self):
        """Perform a step in the memory manager - Some memory managers may need to perform some action every step"""
        pass
    
    def reached_conversation_limit(self):
        """Ran when the conversation limit is reached, or the conversation is ended - Some memory managers may need to perform some action when the conversation limit is reached"""
        logging.info("Conversation limit reached. Saving conversation history and generating a summary.")
        self.save_conversation()

    def add_message(self, message):
        """Add a message to the memory manager - This memory manager does not need to perform any action when a message is added"""
        pass

    @property
    def latest_summary(self):
        """Return a string representation of the memories stored in the memory manager - Some memory managers have updating memories strings"""
        if os.path.exists(self.latest_conversation_summary_file_path): # if the conversation summary file exists, load the conversation summary from the conversation summary file
            with open(self.latest_conversation_summary_file_path, 'r', encoding='utf-8') as f: # load the conversation summary from the conversation summary file
                return f.read()
        else: # if the conversation summary file does not exist, return a warning message
            return ""

    @property
    def memories(self):
        memories = [
            {
                "role": self.config.system_name,
                "content": "The following is a summary of "+self.name+"'s memories of what they've done/discussed."
            },
            {
                "role": self.config.system_name,
                "content": self.latest_summary
            }
        ]
        return memories
    
    @property
    def memory_offset(self):
        """Return the memory depth of the character"""
        return self.config.summarizing_memory_depth
    
    @property
    def memory_offset_direction(self):
        """Return the memory offset direction of the character"""
        return self.config.summarizing_memory_direction