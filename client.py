import argparse
from mongo import *
from datetime import timedelta, datetime
from dateutil import tz

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

# help, download (v), mongo, from, to, day, time
parser = argparse.ArgumentParser(prog='CeskeDrahyFinder')
parser.add_argument('--day', help='day of departure')
parser.add_argument('--month', help='month of departure')
parser.add_argument('--year', help='year of departure')
parser.add_argument('--time', help='departure time, time format HH:MM')
parser.add_argument('--from', help='which station you depart from')
parser.add_argument('--to', help='your destination station')
args = vars(parser.parse_args())

try:
  print(iso_converter(args["day"],args["month"],args["year"],args["time"]))
except:
  parser.print_help()

# zruseni vlaku -- DONE
# nahradni trasa -- IN PROGRESS