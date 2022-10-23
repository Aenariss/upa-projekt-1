import argparse
from mongo import *
from datetime import timedelta, datetime
from dateutil import tz
from getData import Downloader
from xml_parser import *

collection_trains = None
collection_canceled = None
collection_changes = None
collection_stations = None

def setup_db():
    global collection_trains
    global collection_canceled
    global collection_changes
    global collection_stations

    db = get_database()
    collection_trains = db["trains"]
    collection_canceled = db["canceled"]
    collection_changes = db["changes"]
    collection_stations = db["stations"]

def trainCanceled(id, date):
    # get = collection_canceled.find_one({"_id":id}) # the same as below, keep just in case
    get = collection_canceled.find_one(id)  # if it wasnt found, we get None type
    if get: # if a train was cancelled, check if the day was also
        # start date
        start_date = get['CZCanceledPTTMessage']['PlannedCalendar']['ValidityPeriod']['StartDateTime']
        end_date = get['CZCanceledPTTMessage']['PlannedCalendar']['ValidityPeriod']['EndDateTime']
        if start_date and end_date:
            d1 = datetime.fromisoformat(start_date)
            d2 = datetime.fromisoformat(end_date) + timedelta(days=1) - timedelta(seconds=1)  # end date is the day when it ends, aka the last day of the cancelation, so add + 1 dat to this and subtract 1 second
            date = datetime.fromisoformat(date)

            # time makes sense, jut a check (they would NOT cancel it so that the cancellation ends before it begins... surely not...)
            if (d1 <= date <= d2):
                index = (date-d1).days
                try:
                    bitDay = get['CZCanceledPTTMessage']['PlannedCalendar']['BitmapDays'][index]
                    return bitDay == '1'  # returns 1 if canceled, 0 if not
                # If the bit day is not set or something is broken in some other way, lets suppose the train runs
                except:
                    return False
            else:
                return False

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

def exist_changed_plan(train, from_station, to_station, dt)-> dict:
    ...

def get_route(trains:list, from_station, to_station, dt:datetime):
    for train in trains:
        if trainCanceled(train, dt.isoformat()):
            if exist_changed_plan(train, from_station, to_station, dt):
                ...
            trains.remove(train)

    hour = dt.hour
    minute = dt.minute
    time_int = int(hour)*100 + minute
    aggregate_query = [{
        '$match': {
                    'CZPTTCISMessage.Identifiers.PlannedTransportIdentifiers.Core': {"$in": trains}
                }
    },
        {
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
    min_value = 3000
    min_result = None
    for result in query_result:
        CZPTTLocation = result["CZPTTCISMessage"]["CZPTTInformation"]["CZPTTLocation"]
        calendar = result["CZPTTCISMessage"]["CZPTTInformation"]["PlannedCalendar"]
        day_bitmap = calendar["BitmapDays"]
        date_start = calendar["ValidityPeriod"]["StartDateTime"] + "-00:00"
        d1 = datetime.fromisoformat(date_start)
        index = (dt - d1).days
        try:
            bitDay = day_bitmap[index]
            if bitDay == "0":  # returns 1 if canceled, 0 if not
                break
        # If the bit day is not set or something is broken in some other way, lets suppose the train runs
        except:
            break

        for location in CZPTTLocation:
            station = location["Location"]["PrimaryLocationName"]
            if station == from_station:
                timings = location["TimingAtLocation"]["Timing"]
                if type(timings) is not list:
                    timings = [timings]
                for timing in timings:
                    if timing["@TimingQualifierCode"] == "ALD":
                        if min_value > timing["time_int"] >= time_int:
                            min_value = timing["time_int"]
                            min_result = result["CZPTTCISMessage"]

            if station == to_station:
                break
    return min_result
def print_route(CZPTTCISMessage:dict, from_station, to_station):
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
        if station == to_station:
            break

def iso_converter(day, month, year, time):
    current_date = datetime.now()
    if year == None:
        year = current_date.year
    if month == None:
        month = current_date.month
    if day == None:
        day = current_date.day
    if time == None:
        time = current_date.time
    hour = time[:-3]
    min = time[3:]
    zone = tz.gettz('Europe / Berlin') 
    date = datetime(year=int(year),month=int(month),day=int(day),hour=int(hour),minute=int(min),tzinfo=zone)
    return date.isoformat()

if __name__ == '__main__':
    setup_db()
    s_from = "Slaný předměstí"
    s_to = "Chlumčany u Loun"
    for i in range(10, 30):
        date_str = f"2022-05-{i}T00:00:00.000-00:00"

        #trains = find_common(s_from, s_to)
        trains = ["KT----10208A"]
        dt = datetime.fromisoformat(date_str)
        route = get_route(trains, s_from, s_to, dt)
        print_route(route, s_from, s_to)
        print("------------------")


# help, download (v, --unzip), xml parser, from, to, day, time
parser = argparse.ArgumentParser(prog='CeskeDrahyFinder')
subs = parser.add_subparsers()

download_parser = subs.add_parser('download')
download_parser.add_argument('-u', help='unzip downloaded files', action='store_true')
download_parser.add_argument('-v', help='verbose mode', action='store_true')

client_parser = subs.add_parser('client')
client_parser.add_argument('--day', help='day of departure')
client_parser.add_argument('--month', help='month of departure')
client_parser.add_argument('--year', help='year of departure')
client_parser.add_argument('--time', help='departure time, time format HH:MM')
client_parser.add_argument('--from', help='which station you depart from')
client_parser.add_argument('--to', help='your destination station')

xml_parser = subs.add_parser('parser')
xml_parser.add_argument('-x', help='xml',required=True, action='store_true')
args = vars(parser.parse_args())

if(len(args) == 6):
    # client mode
    try:
        print(iso_converter(args["day"],args["month"],args["year"],args["time"]))
    except:
        parser.print_help()

if(len(args)== 2):
    # downloader mode
    try:
        downloader = Downloader()
        downloader.getFiles()
        if args["u"] == True:
            downloader.unzipFolders()
    except:
        parser.print_help()

if(len(args)== 1):
    # xml parser mode
    try:
        setup_db()
        #tmp_push()
    except:
        parser.print_help()

# zruseni vlaku -- DONE
# nahradni trasa -- IN PROGRESS