import logging
import argparse
import json

import src.conversation_manager as cm
import src.config_loader as config_loader
import src.character_db as character_db

try:
    config = config_loader.ConfigLoader() # Load config from config.json
except Exception as e:
    logging.error(f"Error loading config:")
    logging.error(e)
    input("Press Enter to exit.")
    raise e
    
parser = argparse.ArgumentParser(description='Converts csv db to json db or vice versa')
if __name__ == '__main__':
    parser.add_argument('path', type=str, help='The output path for the new db')
    args = parser.parse_args()
    
    conversation_manager = cm.conversation_manager(config, initialize=False) # Partially load conversation manager

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
    