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
                    return bool(bitDay)  # returns 1 if canceled, 0 if not
                # If the bit day is not set or something is broken in some other way, lets suppose the train runs
                except:
                    return False
            else:
                return False

def find_common(odkud, kam):
    # spolecne vlaky pro odkud a kam
    # https://stackoverflow.com/a/42302818/13279982
    tmp = [
            { "$match": { "_id": { "$in": [ "Studénka", "Ostrava-Svinov" ] } } },   # find matching records
            { "$group": { "_id": 0, "first": { "$first": "$pa" }, "second": { "$last": "$pa" } } },     # remove duplicates
            { "$project": { "cores": { "$setIntersection": [ "$first", "$second" ] }, "_id": 0 } }      # create a result
        ]
    result = collection_stations.aggregate(tmp)
    try:
        result = list(result)[0]['cores']
    except:
        result = []
    return result

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
    print(trainCanceled('KT------694A', '2021-12-12T00:00:00'))

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