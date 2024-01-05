import argparse

import src.config_loader as config_loader
import src.character_db as character_db
import src.config_loader as config_loader

    
parser = argparse.ArgumentParser(description='Converts csv db to json db or vice versa')
if __name__ == '__main__':
    parser.add_argument('path1', type=str, help='The input file or directory path')
    parser.add_argument('path2', type=str, help='The output directory or file path')
    args = parser.parse_args()

    config = config_loader.ConfigLoader("./config.ini")
    config.character_df_file = args.path1
    db = character_db.CharacterDB(config)

    if args.path2.endswith('.csv'):
        print("Saving to csv...")
        db.save(args.path2, "csv")
    else:
        print("Saving to json...")
        db.save(args.path2, "json")
        
    new_config = config_loader.ConfigLoader("./config.ini")
    new_config.character_df_file = args.path2
    new_db = character_db.CharacterDB(new_config)

    diff = db.compare(new_db)
    print("Total differences: " + str(len(diff)))
    print("Differences: " + str(diff))
    