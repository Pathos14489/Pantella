
from  src.logging import logging
import os
print(os.path.dirname(__file__))
import src.conversation_manager as cm
import src.config_loader as config_loader
import src.utils as utils
import argparse
import src.character_db as character_db
import json
import traceback

print("Starting Pantella Database Conversion Script")
try:
    config = config_loader.ConfigLoader() # Load config from config.json
except Exception as e:
    logging.error(f"Error loading config:")
    logging.error(e)
    tb = traceback.format_exc()
    logging.error(tb)
    input("Press Enter to exit.")
    raise e

utils.cleanup_mei(config.remove_mei_folders) # clean up old instances of exe runtime files
    
parser = argparse.ArgumentParser(description='Converts csv db to json db or vice versa')
if __name__ == '__main__':
    parser.add_argument('path', type=str, help='The output path for the new db')
    parser.add_argument('--output', type=str, help='path to output patch file')
    args = parser.parse_args()
    
    print("Creating Conversation Manager")
    try:
        conversation_manager = cm.create_manager(config, initialize=False) # Partially load conversation manager
    except Exception as e:
        logging.error(f"Error Creating Conversation Manager:")
        logging.error(e)
        tb = traceback.format_exc()
        logging.error(tb)
        input("Press Enter to exit.")
        raise e

    if args.path.endswith('.csv'):
        logging.info("Saving to csv...")
        conversation_manager.character_database.save(args.path, "csv")
    else:
        logging.info("Saving to json...")
        conversation_manager.character_database.save(args.path, "json")
        
    new_db = character_db.CharacterDB(conversation_manager) # Load newly created db

    diff = conversation_manager.character_database.compare(new_db)
    if len(diff) < 100:
        print("Differences: " + str(diff))
    else:
        print("Too many differences to print to console, set --output to output to file")
    logging.info("Total differences: " + str(len(diff)))
    if parser.parse_args().output:
        with open(parser.parse_args().output, 'w') as f:
            json.dump(diff, f)
    