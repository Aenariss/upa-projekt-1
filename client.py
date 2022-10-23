from mongo import *
from datetime import timedelta, datetime
from mongo import *
from xml_parser import trainStopsInStation

collection_trains = None
collection_canceled = None
collection_changes = None
collection_stations = None

def setup_db():
    global collection_trains
    global collection_canceled
    global collection_changes
    global collection_stations

    #client = get_client()
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

if __name__ == '__main__':
    setup_db()
    print(trainCanceled('KT------694A', '2021-12-12T00:00:00'))

# zruseni vlaku -- DONE
# nahradni trasa -- IN PROGRESS