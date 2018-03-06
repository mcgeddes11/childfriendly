from shapely.geometry import LineString
import pandas, numpy
a = LineString([(0, 0), (1, 1)]).centroid

import pyproj
import shapefile
from pyproj import Proj, transform
sf = shapefile.Reader("/media/sf_VBoxShared/childf/census_subdivisions/lcsd000a16a_e.shp")
shapes = sf.shapes()
records = sf.records()

shape_recs = []
# Iterate over every record in the shapefile, finding the centroid and converting to lat/long
for ix, shp in enumerate(shapes):
    d = {}
    c = LineString(shp.points).centroid
    p = pyproj.Proj(
        "+proj=lcc +lat_1=49 +lat_2=77 +lat_0=63.390675 +lon_0=-91.86666666666666 +x_0=6200000 +y_0=3000000 +ellps=GRS80 +towgs84=0,0,0,0,0,0,0 +units=m +no_defs")
    lon, lat = p(c.x, c.y, inverse=True)
    for jx, f_name in enumerate(sf.fields):
        if jx == 0:
            continue
        d[f_name[0]] = records[ix][jx-1]
    d["lat"] = lat
    d["lon"] = lon
    shape_recs.append(d)
df = pandas.DataFrame.from_records(shape_recs)
a = numpy.unique([len(str(x)) for x in df["CSDUID"].values])
print df


data = pandas.read_csv("/home/user/data/childfriendly/Raw/census_data.csv", nrows=500000)










    # import pandas, numpy
# data = pandas.read_csv("/home/user/data/childfriendly/Raw/census_data.csv")
# print "foo"
#
# province_codes = numpy.array([str(x).zfill(2)[0:2] for x in data["GEO_CODE (POR)"].values])
# # Only get BC
# data = data = data[province_codes=="59"]
# # Only get age <= 18
# # data = data[data["Member ID: Age (in single years) and average age (127)"] <= 18]
# data = data[data["GEO_LEVEL"] == 3]
# lens = numpy.array([len(x) for x in data["DIM: Age (in single years) and average age (127)"].values])
# ix = (lens < 3) | (data["DIM: Age (in single years) and average age (127)"] == "Under 1 year")
# data = data[ix]
# data.loc[data["DIM: Age (in single years) and average age (127)"] == "Under 1 year","DIM: Age (in single years) and average age (127)"] = 0