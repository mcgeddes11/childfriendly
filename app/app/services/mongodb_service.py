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
        curs = collection.find(filter, projection=projection)
    else:
        curs = collection.find(filter)
    client.close()
    recs = [x for x in curs]
    return recs

def mg_get_near(collection_name, lat, lon, dist_in_m):
    client = MongoClient(conn_str)
    db = client[db_name]
    collection = db[collection_name]
    curs = collection.find({ "location": { "$nearSphere": { "$geometry": { "type": "Point", "coordinates": [ lon, lat ] }, "$maxDistance": dist_in_m } } })
    recs = [x for x in curs]
    client.close()
    return recs

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
