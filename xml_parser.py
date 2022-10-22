import os.path
import sys
import argparse
import xmltodict
from xml.parsers.expat import ExpatError
from mongo import *
import traceback
from datetime import datetime

collection_trains = None
collection_canceled = None
collection_changes = None


def setup_db():
    global collection_trains
    global collection_canceled
    global collection_changes

    # Get the database
    get_databases()
    # `app` is name of db, `trains` is name of collection
    create_collection("app", "trains")
    create_collection("app", "canceled")
    create_collection("app", "changes")
    # get_database `app` our database we dont need anything else imo
    dbname = get_database()
    collection_trains = dbname["trains"]
    collection_canceled = dbname["canceled"]
    collection_changes = dbname["changes"]


def create_arg_parser():
    # Creates and returns the ArgumentParser object

    parser = argparse.ArgumentParser(description='UPA project xml parser')
    parser.add_argument('inputDirectory',
                        help='Path to the input directory.')
    return parser


def get_location_time(CZPTTLocation) -> None:
    """
    Adding integer value of time in each location as integer 1040 -> 10:40, 520 -> 5:20
    this value is inserted into each CZPTTLocation
    :param CZPTTLocation: CZPTTLocation dict
    :return: None
    """
    for location in CZPTTLocation:
        try:
            timings = location["TimingAtLocation"]["Timing"]
            if type(timings) is not list:
                timings = [timings]
            for t in timings:
                hour = t["Time"][:2]
                minute = t["Time"][3:5]
                t["time_int"] = int(hour) * 100 + int(minute)
        except KeyError as ke:  # some records don't have Timing
            pass


def parse_xml_dir(path: str = "./xmls"):
    xml_errors = []
    json_errors = []
    for root, dirs, files in os.walk(path):
        print(root)
        for file in files:
            with open(os.path.join(root, file), "rb") as xml_file:
                try:
                    data_dict = xmltodict.parse(xml_file.read())
                    try:
                        if root == "./xmls":
                            get_location_time(data_dict["CZPTTCISMessage"]["CZPTTInformation"]["CZPTTLocation"])
                            collection_trains.insert_one(data_dict)

                        else:

                            if "cancel_" in xml_file.name:
                                collection_canceled.insert_one(data_dict)
                            else:
                                collection_changes.insert_one(data_dict)

                    except TypeError as te:
                        traceback.print_exc()
                        json_errors.append(file)
                except ExpatError as ee:
                    xml_errors.append(file)

    print(f"XML errors: {len(xml_errors)}")
    print(f"JSON errors: {len(json_errors)}")


def get_valid_route(from_station, to_station, hour, minute) -> dict:
    time_int = int(hour)*100 + int(minute)
    aggregate_query = [
    {
        '$match': {
            'CZPTTCISMessage.CZPTTInformation.CZPTTLocation.Location.PrimaryLocationName': f'{from_station}'
        }
    }, {
        '$match': {
            'CZPTTCISMessage.CZPTTInformation.CZPTTLocation.Location.PrimaryLocationName': f'{to_station}'
        }
    }, {
        '$match': {
            '$and': [
                {
                    'CZPTTCISMessage.CZPTTInformation.CZPTTLocation.Location.PrimaryLocationName': f'{from_station}'
                },
                {
                    'CZPTTCISMessage.CZPTTInformation.CZPTTLocation.TimingAtLocation.Timing.time_int': {
                        '$gte': time_int
                    }
                }
            ]
        }
    }
]
    query_result = collection_trains.aggregate(aggregate_query)
    for result in query_result:
        message = result['CZPTTCISMessage']
        CZPTTLocation = message["CZPTTInformation"]["CZPTTLocation"]
        for location in CZPTTLocation:
            station = location["Location"]["PrimaryLocationName"]
            if station == to_station:
                break
            if station == from_station:
                return message

    return {}



def time_to_int(hours, minutes):
    return int(hours)*100 + int(minutes)


def print_route(CZPTTCISMessage:dict, from_station, to_station):
    CZPTTLocation = CZPTTCISMessage["CZPTTInformation"]["CZPTTLocation"]
    print_out = False
    for location in CZPTTLocation:
        station = location["Location"]["PrimaryLocationName"]
        if station == from_station:
            print_out = True
        if print_out:
            timings = location["TimingAtLocation"]["Timing"]
            if type(timings) is not list:
                timings = [timings]
            for timing in timings:
                if timing["TimingQualifierCode"] == "ALD":
                    print(f'{timing["Time"]} - {station}')
        if station == to_station:
            break


if __name__ == "__main__":
    arg_parser = create_arg_parser()
    parsed_args = arg_parser.parse_args(sys.argv[1:])
    if not os.path.exists(parsed_args.inputDirectory):
        print("Directory not exists")
        sys.exit(1)
    setup_db()

    # parse_xml_dir(parsed_args.inputDirectory)
    from_station = "Brno hl. n."
    to_station = "Brno-Řečkovice"

    today = datetime.today()
    route = get_valid_route(from_station, to_station, 22, 30)
    print_route(route, from_station, to_station)


    """
    # get routes
    query1 = {"CZPTTCISMessage.CZPTTInformation.CZPTTLocation.Location.PrimaryLocationName": from_station}
    query2 = {"CZPTTCISMessage.CZPTTInformation.CZPTTLocation.Location.PrimaryLocationName": to_station}
    # check stations order

    query_list = []
    query_list.append(query1)
    query_list.append(query2)

    if len(query_list) > 1:
        result = collection_trains.find({"$and": query_list})
    else:
        result = collection_trains.find(query_list[0])

    """