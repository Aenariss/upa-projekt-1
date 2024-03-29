## XML Parser to parse data
# UPA Project 1
# Author: Vojtech Giesl <xgiesl00>, Vojtech Fiala <xfiala61>, Vojtech Kronika <xkroni01>

import os.path
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

def parse_xml_dir(collection_trains, collection_stations, path: str = "./xmls"):
    xml_errors = []
    json_errors = []
    root_files = 0
    canceled_num = 0
    changes_num = 0

    dirs = []
    print(f"parsing {path}")
    for filename in os.listdir(path):
        # first iterate files in root dir
        d = os.path.join(path, filename)
        if os.path.isdir(d):
            dirs.append(d)
        else:
            #regular file
            with open(os.path.join(path, filename), "rb") as xml_file:
                try:
                    data_dict = xmltodict.parse(xml_file.read())
                    root_files += 1
                    id = getID(data_dict)  # always save core PA
                    data_dict['_id'] = id
                    get_location_time(data_dict["CZPTTCISMessage"]["CZPTTInformation"]["CZPTTLocation"])
                    location_collection(data_dict, collection_stations)
                    collection_trains.replace_one({'_id': id}, data_dict, upsert=True)
                except ExpatError as ee:
                    xml_errors.append(filename)

    # process sub dirs
    change_files = []
    for directory in dirs:
        print(f"parsing {directory}")
        for filename in os.listdir(directory):
            file_path = os.path.join(directory, filename)
            if "cancel_" not in file_path:
                change_files.append(file_path)
            else:
                with open(file_path, "rb") as xml_file:
                    try:
                        canceled_num += 1
                        data_dict = xmltodict.parse(xml_file.read())
                        canceledMessageParse(data_dict, collection_trains)
                        # print('ok')
                    except TypeError as te:
                        traceback.print_exc()
                        json_errors.append(filename)

    print(f"parsing {len(change_files)} files with change")
    for file_path in change_files:
        if changes_num % 1000 == 0:
            print(f"parsed {changes_num}/{len(change_files)} files")

        with open(file_path, "rb") as xml_file:
            try:
                data_dict = xmltodict.parse(xml_file.read())
                changes_num += 1
                id = getID(data_dict)
                data_dict["_id"] = id
                orig_train_id = getIDReplaced(data_dict)  # if None, there is no original train
                if orig_train_id:  # original trains which this one replaces was found
                   orig_train = collection_trains.find_one(
                       {"_id": orig_train_id})  # get the original train's info
                   if not orig_train:  # cancelation message doesnt cancel anything
                       pass  # if original was not found, just put this new one into the collection
                   else:
                       start_date = \
                           data_dict['CZPTTCISMessage']['CZPTTInformation']['PlannedCalendar']['ValidityPeriod'][
                               'StartDateTime']
                       end_date = \
                           data_dict['CZPTTCISMessage']['CZPTTInformation']['PlannedCalendar']['ValidityPeriod'][
                               'EndDateTime']
                       newBitField = data_dict['CZPTTCISMessage']['CZPTTInformation']['PlannedCalendar'][
                           'BitmapDays']

                       orig_start = \
                           orig_train['CZPTTCISMessage']['CZPTTInformation']['PlannedCalendar']['ValidityPeriod'][
                               'StartDateTime']
                       bitDayField = orig_train['CZPTTCISMessage']['CZPTTInformation']['PlannedCalendar'][
                           'BitmapDays']

                       newBitField = invertBitField(
                           newBitField)  # inverse the new one, to replace the old (aka when new is 1, old is 0)

                       if start_date and end_date:
                           d1 = datetime.fromisoformat(start_date)
                           d2 = datetime.fromisoformat(end_date)
                           bit_changing_length = (d2 - d1 + timedelta(
                               days=1)).days  # if begins and ends on the same day, it lasts for only a day, aka result is 0, so i need to always add +1

                           d3 = datetime.fromisoformat(orig_start)
                           begin_index = (
                                   d1 - d3).days  # neww_start - old start tells me the index when the new one begins
                           new_bitmap = bitDayField[:begin_index] + newBitField + bitDayField[
                                                                                  begin_index + bit_changing_length:]

                           orig_train['CZPTTCISMessage']['CZPTTInformation']['PlannedCalendar'][
                               'BitmapDays'] = new_bitmap

                           collection_trains.replace_one({'_id': orig_train_id}, orig_train, upsert=True)

                   get_location_time(data_dict["CZPTTCISMessage"]["CZPTTInformation"]["CZPTTLocation"])
                   location_collection(data_dict, collection_stations)
                   collection_trains.replace_one({'_id': id}, data_dict, upsert=True)

                else:  # this is an original train, so act like it
                   get_location_time(data_dict["CZPTTCISMessage"]["CZPTTInformation"]["CZPTTLocation"])
                   location_collection(data_dict, collection_stations)
                   collection_trains.replace_one({'_id': id}, data_dict, upsert=True)
            except TypeError as te:
                traceback.print_exc()
                json_errors.append(filename)

    print(f"Parsed \n {root_files} root files \n {canceled_num} - canceled files \n {changes_num} - changed files ")

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

# Doesnt really invert, just if its 1, turn it to 0
def invertBitField(bitfield):
    new_field = []
    for i in bitfield:
        if i == '1':
            new_field.append('0')
        else:
            new_field.append(i)
    new_field = ''.join(new_field)
    return new_field


def canceledMessageParse(orig_msg, collection_trains):
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
            x = '0001' == activityType['TrainActivityType']
            if not x: 
                return 0
        except:
            flag = 0
            for i in activityType:
                if '0001' == i['TrainActivityType']:
                    flag = 1
            if not flag:
                return 0
    except:
        return 0    # train doesnt stop here
    return 1

def location_collection(data_dict, collection_stations):
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

def time_to_int(hours, minutes):
    return int(hours)*100 + int(minutes)

if __name__ == "__main__":
    setup_db()
    parse_xml_dir(collection_trains, collection_stations)
