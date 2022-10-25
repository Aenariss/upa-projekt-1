## Client to run the app
# UPA Project 1
# Author: Vojtech Kronika <xkroni01>, Vojtech Giesl <xgiesl00>, Vojtech Fiala <xfiala61>

import argparse
from mongo import *
from datetime import timedelta, datetime
from dateutil import tz
from getData import Downloader
import traceback
from xml_parser import trainStopsInStation, parse_xml_dir

collection_trains = None
collection_stations = None

def setup_db():
    global collection_trains
    global collection_stations

    db = get_database()
    collection_trains = db["trains"]
    collection_stations = db["stations"]

def find_common(odkud, kam):
    # spolecne vlaky pro odkud a kam
    # https://stackoverflow.com/a/42302818/13279982
    tmp = [
            { "$match": { "_id": { "$in": [ odkud, kam ] } } },   # find matching records
            { "$group": { "_id": 0, "first": { "$first": "$pa" }, "second": { "$last": "$pa" } } },     # remove duplicates
            { "$project": { "cores": { "$setIntersection": [ "$first", "$second" ] }, "_id": 0 } }      # create a result
        ]
    result = collection_stations.aggregate(tmp)
    try:
        result = list(result)[0]['cores']
    except:
        result = []
    return result

def find_similar(station):
    query = {"_id": { "$regex": "^"+station, "$options": "si" } }  # find matching records
    try:
        result = collection_stations.find_one(query)["_id"]
    except:
        result = []
    return result

def exist_changed_plan(train, from_station, to_station, dt)-> dict:
    ...

def get_route(trains:list, from_station, to_station, dt:datetime):

    hour = dt.hour
    minute = dt.minute
    time_int = int(hour)*100 + minute


    aggregate_query = [
        {'$match': { 'CZPTTCISMessage.Identifiers.PlannedTransportIdentifiers.0.Core': {"$in": trains}}},
        {'$match':
            {'$and': [{ 'CZPTTCISMessage.CZPTTInformation.CZPTTLocation.Location.PrimaryLocationName': f'{from_station}'},
                      {'CZPTTCISMessage.CZPTTInformation.CZPTTLocation.TimingAtLocation.Timing.time_int': {'$gte': time_int}}]}},
        ]


    query_result = collection_trains.aggregate(aggregate_query)

    min_value = 3000
    min_result = None
    for result in query_result:
        CZPTTLocation = result["CZPTTCISMessage"]["CZPTTInformation"]["CZPTTLocation"]
        calendar = result["CZPTTCISMessage"]["CZPTTInformation"]["PlannedCalendar"]
        day_bitmap = calendar["BitmapDays"]
        date_start = calendar["ValidityPeriod"]["StartDateTime"] + "-00:00"
        d1 = datetime.fromisoformat(date_start)
        index = (dt - d1).days
        if index > len(day_bitmap) or index < 0: # out of bounds
            continue
        try:
            bitDay = day_bitmap[index]
            if bitDay == "0":  # if its cancelled that day, try another one
                continue
        # If the bit day is not set or something is broken in some other way, continue
        except:
            continue

        from_time = 0
        to_time = 2500
        for location in CZPTTLocation:
            station = location["Location"]["PrimaryLocationName"]
            if station == to_station:
                if not trainStopsInStation(location):
                    break
                try:
                    to_time = location["TimingAtLocation"]["Timing"][0]['time_int']
                except:
                    to_time = location["TimingAtLocation"]["Timing"]['time_int']

            if station == from_station:
                if not trainStopsInStation(location):
                    break
                try:
                    from_time = location["TimingAtLocation"]["Timing"][0]['time_int']
                except:
                    from_time = location["TimingAtLocation"]["Timing"]['time_int']
                timings = location["TimingAtLocation"]["Timing"]
                if type(timings) is not list:
                    timings = [timings]
                for timing in timings:
                    if timing["@TimingQualifierCode"] == "ALD":
                        if min_value > timing["time_int"] and timing["time_int"] >= time_int and from_time < to_time:
                            min_value = timing["time_int"]
                            min_result = result["CZPTTCISMessage"]
            if station == to_station:   # the train found
                break

    return min_result

def print_route(CZPTTCISMessage:dict, from_station, to_station):
    
    print(f"Route from {from_station} to {to_station} ")
    print("-------------------------------")
    if CZPTTCISMessage is None:
        print("No route in selected day")
        return

    CZPTTLocation = CZPTTCISMessage["CZPTTInformation"]["CZPTTLocation"]
    print_out = False

    for location in CZPTTLocation:
        station = location["Location"]["PrimaryLocationName"]
        if station == from_station:
            print_out = True
        if print_out:
            if trainStopsInStation(location):
                timings = location["TimingAtLocation"]["Timing"]
                if type(timings) is not list:
                    timings = [timings]
                for timing in timings:
                    if timing["@TimingQualifierCode"] == "ALD":
                        print(f'{timing["Time"][:8]} (GMT{timing["Time"][-6:]}) - {station}')

                    else:   # when the train doesnt continue, it only has an arrival time
                        if station == to_station:
                            print(f'{timing["Time"][:8]} (GMT{timing["Time"][-6:]}) - {station}')
                            break
        if station == to_station:
            break
    print("-------------------------------")

def iso_converter(day, month, year, time):
    current_date = datetime.now()
    if year == None:
        year = current_date.year
    if month == None:
        month = current_date.month
    if day == None:
        day = current_date.day
    if time == None:
        tmp = str(current_date)
        time = tmp[11:-10]
    hour = time[:-3]
    min = time[3:]
    zone = tz.gettz('Europe / Berlin') 
    date = datetime(year=int(year),month=int(month),day=int(day),hour=int(hour),minute=int(min),tzinfo=zone)
    return date

if __name__ == '__main__':
    setup_db()
    # help, download (v, --unzip), xml parser, from, to, day, time
    parser = argparse.ArgumentParser(prog='CeskeDrahyFinder')
    subs = parser.add_subparsers()

    download_parser = subs.add_parser('download')
    download_parser.add_argument('-u', help='unzip downloaded files. Files must be downloaded before this command.', action='store_true')
    download_parser.add_argument('-v', help='verbose mode', action='store_true')

    client_parser = subs.add_parser('client')
    client_parser.add_argument('--day', help='day of departure')
    client_parser.add_argument('--month', help='month of departure')
    client_parser.add_argument('--year', help='year of departure')
    client_parser.add_argument('--time', help='departure time, time format HH:MM')
    client_parser.add_argument('--from', help='which station you depart from')
    client_parser.add_argument('--to', help='your destination station')

    xml_parser = subs.add_parser('parser')
    xml_parser.add_argument('--path', help='path to directory with xml files')
    args = vars(parser.parse_args())

    if(len(args) == 6):
        # client mode
        try:
            date = iso_converter(args["day"], args["month"], args["year"], args["time"])
            from_station = args["from"]
            to_station = args["to"]

            trains = find_common(from_station, to_station)
            try: 
                print(date.strftime('Departure at %d. %b %Y Time: %H:%M'))
                dt = datetime.fromisoformat(date.isoformat() + "+00:00")
                route = get_route(trains, from_station, to_station, dt)
                print_route(route, from_station, to_station)

            except Exception as e:
                traceback.print_exc() 

        except:
            parser.print_help()

    if(len(args)== 2):
        # downloader mode
        try:
            verbose = args['v']
            downloader = Downloader(verbose)
            if args["u"] == True:
                downloader.unzipFolders()
                print("files unzipped successfully")
            else:
                downloader.getFiles()
                print("files download successfully")
        except:
            parser.print_help()

    if(len(args)== 1):
        # xml parser mode
        try:
            path = args["path"]
            if path == None:
                parse_xml_dir(collection_trains, collection_stations)
            else:
                parse_xml_dir(collection_trains, collection_stations,path)
            print("XMLS parsed successfully")
        except:
            parser.print_help()