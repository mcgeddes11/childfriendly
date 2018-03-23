from mongodb_service import *
from math import sin, cos, sqrt, atan2, radians
from scipy.spatial.distance import cosine, euclidean
from scipy.stats import zscore
from sklearn.preprocessing import MinMaxScaler
import numpy

def compute_score(lat, lon, age):

    # Get local data using coords
    # TODO: need to make sure we get at least n points
    census_data = mg_get_near("census", lat, lon, 20000)[0:5]
    crime_data = mg_get_near("crime", lat, lon, 20000)[0:5]
    school_data = mg_get_near("schools", lat, lon, 20000)[0:5]
    traffic_data = mg_get_near("traffic", lat, lon, 20000)[0:5]

    # Select top 5 to compute scores
    census_data = census_data[0:5]
    crime_data = crime_data[0:5]
    school_data = school_data[0:5]


    # Get all crime data to determine the 1-10 scores
    all_crime = mg_get({},"crime")
    all_crime_scores = numpy.array([x["csi"] for x in all_crime])
    # Get all school scores to determine 1-10 scores
    all_schools = mg_get({},"schools")
    all_school_scores = numpy.array([x["score"] for x in all_schools])
    # Get all traffic data to determine 1-10 scores
    all_traffic = mg_get({},"traffic")
    all_traffic_scores = numpy.array([x["traffic_ratio"] for x in all_traffic])

    # Get all census data for this province
    # TODO: Pass province as argument
    # TODO: Include province code (e.g. BC, AB) in all tables
    # TODO: Include sex of child as a parameter to refine this
    all_census = mg_get({"province_id": "59"},"census")
    # Compute ratios for each census district for comparison purposes
    all_ratios = demographic_ratios_for_age(all_census,age, plusminus=2)



    # Traffic scores - * - * - * - * - * - * - * - *
    # TODO: refine this methodology - maybe use commute times from census data?
    if len(traffic_data) == 0:
        final_traffic_scaled = 0
    else:
        final_traffic_scaler = MinMaxScaler(feature_range=(1,10))
        final_traffic_scaler.fit(all_traffic_scores.reshape(-1,1))
        local_traffic_ratio = numpy.mean([x["traffic_ratio"] for x in traffic_data])
        final_traffic_scaled = final_traffic_scaler.transform(local_traffic_ratio)[0][0]
        final_traffic_scaled = 10 - final_traffic_scaled


    # Demographic score - * - * - * - * - * - * - * - *
    if len(census_data) == 0:
        final_census_scaled = numpy.nan
    else:
        all_ratios = all_ratios[all_ratios > 0]
        all_ratios = numpy.log10(all_ratios)
        census_dists = numpy.array([compute_distance(lat, lon, x["location"]["coordinates"][1], x["location"]["coordinates"][0]) for x in census_data])
        final_census_scaler = MinMaxScaler(feature_range=(1,10))
        final_census_scaler.fit(all_ratios.reshape(-1,1))
        # Get the age cohort ratios for the local data we found
        local_ratios = demographic_ratios_for_age(census_data,age,plusminus=2)
        # Don't need to rescale these based on distance, so we can just take the mean and skip right to the final scaling step
        final_census_score = numpy.mean(local_ratios)
        print "Raw Census " + str(final_census_score)
        final_census_score = numpy.log10(final_census_score)
        final_census_scaled = final_census_scaler.transform(final_census_score)[0][0]

    # School scores #- * - * - * - * - * - * - * - * - * - * - * - * - * - * - * - * - * - * - * - * - *
    if len(school_data) == 0:
        final_school_scaled = numpy.nan
    else:
        final_school_scaler = MinMaxScaler(feature_range=(1, 10))
        final_school_scaler.fit(all_school_scores.reshape(-1, 1))
        school_dists = numpy.array([compute_distance(lat, lon, x["location"]["coordinates"][1], x["location"]["coordinates"][0]) for x in school_data])
        # For now, just compute an overall school score without accounting for age of the child
        # TODO: only consider schools that are appropriate for the age of the child
        school_scores = numpy.array([x["score"] for x in school_data])

        # Need to invert the distances for the weights so the closest ones have larger values
        school_weights = 1 - school_dists / 20

        # This determines the level to which we scale by distance.  The range must contain one.  Wider ranges give us more
        # pronounced scaling by distance.  (0.9,1.1) bounds the closest item to have weight 1.1 and furthest item to have
        # weight 0.9, with all other items weighted within this range.
        # TODO: play with this range
        scaling_range = (0.9, 1.1)

        # Scale the weights
        scaler = MinMaxScaler(feature_range=scaling_range)
        school_weights = scaler.fit_transform(school_weights.reshape(-1, 1))

        # Compute the final school score
        final_school_score = numpy.mean(school_scores * school_weights)
        print "Raw School " + str(final_school_score)
        final_school_scaled = final_school_scaler.transform(final_school_score)[0][0]
    # - * - * - * - * - * - * - * - * - * - * - * - * - * - * - * - * - * - * - * - * - * - * - * - *

    # Crime score - * - * - * - * - * - * - * - *
    if len(crime_data) == 0:
        final_crime_scaled = numpy.nan
    else:
        crime_dists = numpy.array([compute_distance(lat, lon, x["location"]["coordinates"][1], x["location"]["coordinates"][0]) for x in crime_data])
        # Compute an overall crime score
        crime_scores = numpy.array([x["csi"] for x in crime_data])

        all_crime_scores = all_crime_scores[all_crime_scores > 0]
        all_crime_scores = numpy.log10(all_crime_scores)
        final_crime_scaler = MinMaxScaler(feature_range=(1, 10))
        final_crime_scaler.fit(all_crime_scores.reshape(-1, 1))
        # Need to invert the distances for the weights so the closest ones have larger values
        crime_weights = 1 - crime_dists / 20

        # This determines the level to which we scale by distance.  The range must contain one.  Wider ranges give us more
        # pronounced scaling by distance.  (0.9,1.1) bounds the closest item to have weight 1.1 and furthest item to have
        # weight 0.9, with all other items weighted within this range.
        # TODO: play with this range
        scaling_range = (0.8, 1.2)

        # Scale the weights
        scaler = MinMaxScaler(feature_range=scaling_range)
        crime_weights = scaler.fit_transform(crime_weights.reshape(-1, 1))

        # Compute final crime score
        final_crime_score = numpy.mean(crime_weights * crime_scores)
        print "Raw Crime " + str(final_crime_score)
        final_crime_score = numpy.log10(final_crime_score)
        # Do the final 1-10 scaling
        # For crime, high is bad so we have to take the inverse to get a proper score
        final_crime_scaled = 10 - final_crime_scaler.transform(final_crime_score)[0][0]

    #- * - * - * - * - * - * - * - * - * - * - * - * - * - * - * - * - * - * - * - * - * - * - * - *

    print "Scaled Crime: " + str(final_crime_scaled)
    print "Scaled Schools: " + str(final_school_scaled)
    print "Scaled Demographics: " + str(final_census_scaled)
    print "Scaled Traffic: " + str(final_traffic_scaled)

    # Remove Mongo indexes and out data

    d = {"census_score": final_census_scaled,
         "census_raw": [{i: x[i] for i in x if i != '_id'} for x in census_data],
         "crime_score": final_crime_scaled,
         "crime_raw": [ {i: x[i] for i in x if i != '_id'} for x in crime_data],
         "schools_score": final_school_scaled,
         "schools_raw": [ {i: x[i] for i in x if i != '_id'} for x in school_data],
         "traffic_score": final_traffic_scaled,
         "traffic_raw": [ {i: x[i] for i in x if i != '_id'} for x in traffic_data]}
    return d

# Compute distance between 2 lat/lon points, in km
def compute_distance(lat1, lon1, lat2, lon2):
    R = 6373.0

    lat1 = radians(lat1)
    lon1 = radians(lon1)
    lat2 = radians(lat2)
    lon2 = radians(lon2)

    dlon = lon2 - lon1
    dlat = lat2 - lat1

    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))

    distance = R * c
    return distance

def demographic_ratios_for_age(data,age,plusminus=2):
    # Convert to numpy and extract bins
    bins = numpy.array(data[0]["age_demographics"]["age"])
    data = numpy.array(data)
    # Remove those districts with no population
    ix = numpy.array([False if x["total_population"] == 0 else True for x in data])
    data = data[ix]

    # Get index for the age-range we want
    min_age = age - plusminus if age > 2 else 0
    max_age = age + plusminus if age < 16 else 18
    age_ix = (bins >= min_age) & (bins <= max_age)
    # Compute ratios by dividing the sum of the age brackets for male and female by the total population in each district
    # sums = [numpy.sum(numpy.array(x["age_demographics"]["female_count"])[age_ix] + numpy.array(x["age_demographics"]["male_count"])[age_ix]) for x in data]
    ratios = [numpy.sum(numpy.array(x["age_demographics"]["female_count"])[age_ix] + numpy.array(x["age_demographics"]["male_count"])[age_ix]) / float(x["total_population"]) for x in data]
    ratios = numpy.array(ratios)
    # sums = numpy.array(sums)
    return ratios
