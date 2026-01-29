print("Loading character_db.py...")
from src.logging import logging
import os
import importlib
logging.info("Imported required libraries in character_db.py")

with open(os.path.join(os.path.dirname(__file__), "module_banlist"), "r") as f:
    banned_modules = f.read().split("\n")

DB_Types = {}

# Get all DBs from src/conversation_dbs/ and add them to DB_Types
for file in os.listdir(os.path.join(os.path.dirname(__file__), "character_dbs/")):
    if file.endswith(".py") and not file.startswith("__"):
        module_name = file[:-3]
        if module_name in banned_modules:
            logging.warning(f"Skipping banned memory db: {module_name}")
            continue
        logging.info(f"Importing {module_name} from src.character_dbs")
        module = importlib.import_module(f"src.character_dbs.{module_name}")
        DB_Types[module.db_slug] = module    
logging.info("Imported all character_dbs to DB_Types, ready to create a character_db object!")
# print available character_dbs
logging.config(f"Available character_dbs: {DB_Types.keys()}")
# Create DB object using the config provided
    
def create_DB(conversation_manager):
    config = conversation_manager.config
    config.manager_types["character_dbs"] = DB_Types.keys() # Add conversation db types to config
    if config.character_db_type != "auto": # if a specific db is specified
        logging.info(f"Creating Character Database[{config.character_db_type}]")
        logging.config(f"Creating Character Database[{config.character_db_type}] object")
        if config.character_db_type not in DB_Types:
            logging.error(f"Could not find db: {config.character_db_type}! Please check your config.json file and try again!")
            input("Press enter to continue...")
            raise ValueError(f"Could not find db: {config.character_db_type}! Please check your config.json file and try again!")
        module = DB_Types[config.character_db_type]
        if config.game_id not in module.valid_games:
            logging.error(f"Game '{config.game_id}' not supported by db '{module.db_slug}'.")
            input("Press enter to continue...")
            raise ValueError(f"Game '{config.game_id}' not supported by db '{module.db_slug}'.")
        db = module.CharacterDB(conversation_manager)
        return db
    else: # if no specific character_db is specified
        interface_config = config.interface_configs[config.game_id]
        logging.config(f"Creating Character Database[{interface_config['character_db']}] (auto) object")
        module = DB_Types[interface_config['character_db']]
        db = module.CharacterDB(conversation_manager)
        return db