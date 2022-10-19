import os.path
import sys
import argparse
from pathlib import Path
import xmltodict
from xml.parsers.expat import ExpatError
import json
from mongo import *
import traceback

collection = None


def setup_db():
    global collection
    # Get the database
    get_databases()
    # `app` is name of db, `trains` is name of collection
    create_collection("app", "trains")
    # get_database `app` our database we dont need anything else imo
    dbname = get_database()
    collection = dbname["trains"]


def create_arg_parser():
    # Creates and returns the ArgumentParser object

    parser = argparse.ArgumentParser(description='UPA project xml parser')
    parser.add_argument('inputDirectory',
                        help='Path to the input directory.')
    return parser


def process_json(obj: json):
    # Showcase how to use insert https://www.w3schools.com/python/python_mongodb_insert.asp
    # collection.insert_many([item_1,item_2])
    collection.insert_many([obj])


def parse_xml_dir(path: str = "./xmls"):
    xml_errors = []
    json_errors = []
    print(f"parsing xml files")
    for root, dirs, files in os.walk(path):
        for file in files:
            # print(f"parsing: {file}")
            with open(os.path.join(root, file), "rb") as xml_file:
                try:
                    data_dict = xmltodict.parse(xml_file.read())
                    try:
                        collection.insert_one(data_dict)

                    except TypeError as te:
                        traceback.print_exc()
                        json_errors.append(file)
                except ExpatError as ee:
                    xml_errors.append(file)

    print(f"XML errors: {len(xml_errors)}")
    print(f"JSON errors: {len(json_errors)}")


if __name__ == "__main__":

    arg_parser = create_arg_parser()
    parsed_args = arg_parser.parse_args(sys.argv[1:])
    if not os.path.exists(parsed_args.inputDirectory):
        print("Directory not exists")
        sys.exit(1)
    setup_db()
    parse_xml_dir(parsed_args.inputDirectory)
