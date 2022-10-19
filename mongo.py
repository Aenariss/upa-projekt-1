## A file to upload the data to mongo db
# UPA Project 1
# Author: Vojtech Kronika <xkroni01>

# import the MongoClient class
from pymongo import MongoClient, errors

# global variables for MongoDB host (default port is 27017)
DOMAIN = "0.0.0.0"
PORT = 27017

def get_client():
    return MongoClient(
        host = [ str(DOMAIN) + ":" + str(PORT) ],
        serverSelectionTimeoutMS = 3000, # 3 second timeout
        username = "root",
        password = "upa1",
    )

# creates collection if doesnt exist, also creates database if you choose different than `app`
def create_collection(dbname,colname):
    client = get_client()

    dblist = client.list_database_names()
    if dbname in dblist:
        print("The database exists.")
    else:
        print("The database "+dbname+" created!")

    # create or get database
    mydb = client[dbname]
    # create or get collection
    mycol = mydb[colname]

    collist = mydb.list_collection_names()
    if colname in collist:
        print("The collection exists.")

    # when creating collection or database must not be empty, that's why is tmp file here
    mydict = { "name": "DeleteThis", "address": "Highway 37" }

    mycol.insert_one(mydict)

def get_databases():
    # use a try-except indentation to catch MongoClient() errors
    try:
        # try to instantiate a client instance
        client = get_client()

        # print the version of MongoDB server if connection successful
        print ("server version:", client.server_info()["version"])

        # get the database_names from the MongoClient()
        database_names = client.list_database_names()

    except errors.ServerSelectionTimeoutError as err:
        # set the client and DB name list to 'None' and `[]` if exception
        client = None
        database_names = []

        # catch pymongo.errors.ServerSelectionTimeoutError
        print ("pymongo ERROR:", err)

    print ("\ndatabases:", database_names)

def get_database():
    # use a try-except indentation to catch MongoClient() errors
    try:
        # try to instantiate a client instance
        client = get_client()

    except errors.ServerSelectionTimeoutError as err:
        # set the client and DB name list to 'None' and `[]` if exception
        client = None
        database_names = []

        # catch pymongo.errors.ServerSelectionTimeoutError
        print ("pymongo ERROR:", err)

    return client["app"]
    
  
# This is added so that many files can reuse the function get_databases()
if __name__ == "__main__":   
  
   # Get the database
   get_databases()
   # `app` is name of db, `trains` is name of collection
   create_collection("app","trains")
   # get_database `app` our database we dont need anything else imo
   dbname = get_database()
   collection = dbname["trains"]
   # Show case how to use insert https://www.w3schools.com/python/python_mongodb_insert.asp
   #collection.insert_many([item_1,item_2])
   #collection.insert_one(item_3)
   print(dbname)
   print(collection)
