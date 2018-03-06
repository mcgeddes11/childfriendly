import logging
from os import environ
from pymongo import MongoClient, GEOSPHERE

conn_str = environ.get("CF_DB_CONN_STR", "mongodb://localhost:27017/")
db_name = environ.get("CF_DB_NAME", "childfriendly")



def mg_save(input_data, collection_name):
    client = MongoClient(conn_str)
    db = client[db_name]
    collection = db[collection_name]
    if type(input_data) == dict:
        collection.save(input_data)
    elif type(input_data) == list:
        collection.insert(input_data)
    client.close()

def mg_delete(json_data,collection_name):
    client = MongoClient(conn_str)
    db = client[db_name]
    collection = db[collection_name]
    collection.delete_one(json_data)
    client.close()

def mg_get(filter, collection_name, projection={}):
    client = MongoClient(conn_str)
    db = client[db_name]
    collection = db[collection_name]
    if projection != {}:
        rec = collection.find(filter, projection=projection)
    else:
        rec = collection.find(filter)
    client.close()
    return rec

def mg_drop(collection_name):
    client = MongoClient(conn_str)
    db = client[db_name]
    collection = db[collection_name]
    collection.drop()
    client.close()



def mg_create_geo_index(collection_name, field_name):
    client = MongoClient(conn_str)
    db = client[db_name]
    collection = db[collection_name]
    collection.create_index([(field_name, GEOSPHERE)])
    client.close()
