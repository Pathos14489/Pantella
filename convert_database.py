import logging
import argparse
import json

import src.conversation_manager as cm
import src.character_db as character_db

    
parser = argparse.ArgumentParser(description='Converts csv db to json db or vice versa')
if __name__ == '__main__':
    parser.add_argument('path1', type=str, help='The input file or directory path')
    parser.add_argument('--output', type=str, help='path to output patch file')
    args = parser.parse_args()
    
    conversation_manager = cm.conversation_manager(config_file='config.ini', initialize=False) # Partially load conversation manager

    if args.path1.endswith('.csv'):
        logging.info("Saving to csv...")
        conversation_manager.character_database.save(args.path1, "csv")
    else:
        logging.info("Saving to json...")
        conversation_manager.character_database.save(args.path1, "json")
        
    new_db = character_db.CharacterDB(conversation_manager) # Load newly created db

    diff = conversation_manager.character_database.compare(new_db)
    if len(diff) < 100:
        print("Differences: " + str(diff))
    else:
        print("Too many differences to print to console, set --output to output to file")
    logging.info("Total differences: " + str(len(diff)))
    if args.output:
        with open(args.output, 'w') as f:
            json.dump(diff, f)
    