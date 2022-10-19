import os.path
import sys
import argparse
from pathlib import Path
import xmltodict
from xml.parsers.expat import ExpatError
import json
import zipfile


def create_arg_parser():
    # Creates and returns the ArgumentParser object

    parser = argparse.ArgumentParser(description='UPA project xml parser')
    parser.add_argument('inputDirectory',
                        help='Path to the input directory.')
    return parser


def process_json(obj: json):
    ...

def parse_xml_dir(path: Path):
    xml_errors = []
    json_errors = []
    for filename in os.listdir(path):
        print(filename)
        with open(path + "/" + filename, mode="r", encoding="utf-8") as xml_file:
            try:
                data_dict = xmltodict.parse(xml_file.read())

                try:
                    jo = json.dumps(data_dict)
                    process_json(jo)
                except TypeError:
                    json_errors.append(filename)
            except ExpatError:
                xml_errors.append(filename)

    print(f"XML errors: {len(xml_errors)}")
    print(f"JSON errors: {len(json_errors)}")


if __name__ == "__main__":

    arg_parser = create_arg_parser()
    parsed_args = arg_parser.parse_args(sys.argv[1:])
    if not os.path.exists(parsed_args.inputDirectory):
        print("Directory not exists")
        sys.exit(1)
    parse_xml_dir(parsed_args.inputDirectory)

