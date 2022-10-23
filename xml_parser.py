import os.path
import argparse
import sys
from tracemalloc import start
import xmltodict
from xml.parsers.expat import ExpatError
from mongo import *
import traceback
from datetime import datetime, timedelta

collection_trains = None
collection_stations = None


def setup_db():
    global collection_trains
    global collection_stations


    # Get the database
    db = get_database()

    collection_trains = db["trains"]
    collection_stations = db["stations"]

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
                time = int(hour) * 100 + int(minute)
                t["time_int"] = time

        except KeyError as ke:  # some records don't have Timing
            pass

def parse_xml_dir(path: str = "./xmls"):
    xml_errors = []
    json_errors = []
    for root, dirs, files in os.walk(path):
        print(root)
        for file in files:
            print(file)
            with open(os.path.join(root, file), "rb") as xml_file:
                try:
                    data_dict = xmltodict.parse(xml_file.read())
                    try:
                        if root == "./xmls":
                            id = getID(data_dict)  # always save core PA
                            data_dict['_id'] = id
                            get_location_time(data_dict["CZPTTCISMessage"]["CZPTTInformation"]["CZPTTLocation"])
                            location_collection(data_dict)
                            collection_trains.replace_one({'_id':id}, data_dict, upsert=True)

                        else:
                            if "cancel_" in xml_file.name:
                                canceledMessageParse(data_dict)
                            else:   # replacement trains
                                id = getID(data_dict)
                                data_dict["_id"] = id
                                orig_train_id = getIDReplaced(data_dict)    # if None, there is no original train
                                if orig_train_id:   # original trains which this one replaces was found
                                    orig_train = collection_trains.find_one({"_id":orig_train_id}) # get the original train's info
                                    if not orig_train:    # cancelation message doesnt cancel anything
                                        pass # if original was not found, just put this new one into the collection
                                    else:
                                        start_date = data_dict['CZPTTCISMessage']['CZPTTInformation']['PlannedCalendar']['ValidityPeriod']['StartDateTime']
                                        end_date = data_dict['CZPTTCISMessage']['CZPTTInformation']['PlannedCalendar']['ValidityPeriod']['EndDateTime']
                                        newBitField = data_dict['CZPTTCISMessage']['CZPTTInformation']['PlannedCalendar']['BitmapDays']

                                        orig_start = orig_train['CZPTTCISMessage']['CZPTTInformation']['PlannedCalendar']['ValidityPeriod']['StartDateTime']
                                        bitDayField = orig_train['CZPTTCISMessage']['CZPTTInformation']['PlannedCalendar']['BitmapDays']

                                        newBitField = invertBitField(newBitField)   # inverse the new one, to replace the old (aka when new is 1, old is 0)

                                        if start_date and end_date:
                                            d1 = datetime.fromisoformat(start_date)
                                            d2 = datetime.fromisoformat(end_date) 
                                            bit_changing_length = (d2-d1 + timedelta(days=1)).days   # if begins and ends on the same day, it lasts for only a day, aka result is 0, so i need to always add +1
                                            
                                            d3 = datetime.fromisoformat(orig_start)
                                            begin_index = (d1-d3).days  # neww_start - old start tells me the index when the new one begins
                                            new_bitmap = bitDayField[:begin_index] + newBitField + bitDayField[begin_index+bit_changing_length:]
                                    
                                            orig_train['CZPTTCISMessage']['CZPTTInformation']['PlannedCalendar']['BitmapDays'] = new_bitmap

                                            collection_trains.replace_one({'_id':orig_train_id}, orig_train, upsert=True)
                                    
                                    get_location_time(data_dict["CZPTTCISMessage"]["CZPTTInformation"]["CZPTTLocation"])
                                    location_collection(data_dict)
                                    collection_trains.replace_one({'_id':id}, data_dict, upsert=True)

                                else:   # this is an original train, so act like it
                                    get_location_time(data_dict["CZPTTCISMessage"]["CZPTTInformation"]["CZPTTLocation"])
                                    location_collection(data_dict)
                                    collection_trains.replace_one({'_id':id}, data_dict, upsert=True)

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

def getIDReplaced(xml):
    id = None
    try:
        id = xml['CZPTTCISMessage']['Identifiers']['RelatedPlannedTransportIdentifiers']['Core']
    except:
        pass
    return id


def invertBitField(bitfield):
    new_field = []
    for i in bitfield:
        if i == '0':
            new_field.append('1')
        else:
            new_field.append('0')
    new_field = ''.join(new_field)
    return new_field


def canceledMessageParse(orig_msg):
    # find the id of the message this cancellation is related to
    id = orig_msg['CZCanceledPTTMessage']['PlannedTransportIdentifiers'][0]['Core']   

    original_msg = collection_trains.find_one({"_id":id})

    if not original_msg:    # cancelation message doesnt cancel anything
        return 

    start_date = orig_msg['CZCanceledPTTMessage']['PlannedCalendar']['ValidityPeriod']['StartDateTime']
    end_date = orig_msg['CZCanceledPTTMessage']['PlannedCalendar']['ValidityPeriod']['EndDateTime']
    newBitField = orig_msg['CZCanceledPTTMessage']['PlannedCalendar']['BitmapDays']

    orig_start = original_msg['CZPTTCISMessage']['CZPTTInformation']['PlannedCalendar']['ValidityPeriod']['StartDateTime']
    bitDayField = original_msg['CZPTTCISMessage']['CZPTTInformation']['PlannedCalendar']['BitmapDays']

    newBitField = invertBitField(newBitField)   # inverse the new one, to replace the old (aka when new is 1, old is 0)

    if start_date and end_date:
            d1 = datetime.fromisoformat(start_date)
            d2 = datetime.fromisoformat(end_date) 
            bit_changing_length = (d2-d1 + timedelta(days=1)).days   # if begins and ends on the same day, it lasts for only a day, aka result is 0, so i need to always add +1
            
            d3 = datetime.fromisoformat(orig_start)
            begin_index = (d1-d3).days  # neww_start - old start tells me the index when the new one begins
            new_bitmap = bitDayField[:begin_index] + newBitField + bitDayField[begin_index+bit_changing_length:]
    
    original_msg['CZPTTCISMessage']['CZPTTInformation']['PlannedCalendar']['BitmapDays'] = new_bitmap
    collection_trains.replace_one({'_id':id}, original_msg)

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
    data_dict = xmltodict.parse(xml_file.read())
    data_dict_cancel = xmltodict.parse(xml_file_cancel.read())

    location_collection(data_dict)

    # kdyz existuje cancel message, ziskat ID a vymaskovat bitmap days tak, at tam, kde je v origo 1 a v canceled 0, je 0
    # kdyz existuje nahradni, tak najit origo a tu celou cast nahradit 0 a nahrat tohle mezi normalni rady
    data_dict['_id'] = getID(data_dict)
    collection_trains.insert_one(data_dict)
    data_dict_cancel = canceledMessageParse(data_dict_cancel)

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

if __name__ == "__main__":
    arg_parser = create_arg_parser()
    setup_db()
    parse_xml_dir()
    #tmp_push()