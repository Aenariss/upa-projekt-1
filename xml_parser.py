import os.path
import sys
import argparse
from tracemalloc import start
import xmltodict
from xml.parsers.expat import ExpatError
from mongo import *
import traceback

collection_trains = None
collection_canceled = None
collection_changes = None
collection_stations = None


def setup_db():
    global collection_trains
    global collection_canceled
    global collection_changes
    global collection_stations


    # Get the database
    #get_databases()
    client = MongoClient('mongodb://localhost:27017/')
    db = client['test']

    collection_trains = db["trains"]
    collection_trains.drop()
    collection_canceled = db["canceled"]
    collection_canceled.drop()
    collection_changes = db["changes"]
    collection_changes.drop()

    collection_stations = db["stations"]
    collection_stations.drop()

    # u changed ziskavat ID pres core RelatedPlannedTransportIdentifiers, tim ziskam odkaz rovnou na origo a z origa muzu hned jet tu k tomu... snad jsou unique


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

def getID(xml):
    id = None
    try:
        id = xml['CZPTTCISMessage']['Identifiers']['PlannedTransportIdentifiers'][0]['Core']
    except:
        pass
    return id

def canceledMessageId(orig_msg):
    id = None
    # always take the first PlannedTransportIdentifiers, aka PT Core
    id = orig_msg['CZCanceledPTTMessage']['PlannedTransportIdentifiers'][0]['Core']   
    id_dict = {"_id":id}
    orig_msg = {**id_dict, **orig_msg}
    return orig_msg

def trainStopsInStation(location):
    try:
        activityType = location['TrainActivity']
        try:
            x = '0001' in activityType['TrainActivityType']
            if not x: 
                return 0
        except:
            flag = 0
            for i in activityType:
                if '0001' in i['TrainActivityType']:
                    flag = 1
            if not flag:
                return 0
    except:
        return 0    # train doesnt stop here
    return 1

def location_collection(data_dict):
    id = getID(data_dict) # always save core PA
    stations = data_dict['CZPTTCISMessage']['CZPTTInformation']['CZPTTLocation']
    for location in stations:
        
        # if the activity is not 0001, dont care
        if trainStopsInStation(location):
            location = location['Location']['PrimaryLocationName']

            locations = collection_stations.find_one({'_id':location})
            if not locations:
                locations = []
            else:
                locations = locations['pa']
            locations.append(id)
            collection_stations.replace_one({'_id':location}, {"_id":location, 'pa':locations}, upsert=True)

def tmp_push():
    xml_file = open('./xmls/PA_0054_KT------694A_00_2022.xml', 'rb')
    xml_file_cancel = open('./xmls/2021-12/cancel_PA_0054_KT------694A_00_2022_20211212.xml.xml', 'rb')
    xml_file_cancel_2 = open('./xmls/2021-12/cancel_PA_0054_KT----38548A_00_2022_20211212.xml.xml', 'rb')
    data_dict = xmltodict.parse(xml_file.read())
    data_dict_cancel = xmltodict.parse(xml_file_cancel.read())
    data_dict_cancel_2 = xmltodict.parse(xml_file_cancel_2.read())

    location_collection(data_dict)

    data_dict_cancel = canceledMessageId(data_dict_cancel)
    data_dict_cancel_2 = canceledMessageId(data_dict_cancel_2)

    collection_canceled.insert_one(data_dict_cancel)
    collection_canceled.insert_one(data_dict_cancel_2)
    collection_trains.insert_one(data_dict)

if __name__ == "__main__":

    arg_parser = create_arg_parser()
    #parsed_args = arg_parser.parse_args(sys.argv[1:])
    #if not os.path.exists(parsed_args.inputDirectory):
    #    print("Directory not exists")
    #    sys.exit(1)
    setup_db()
    #parse_xml_dir(parsed_args.inputDirectory)
    tmp_push()
