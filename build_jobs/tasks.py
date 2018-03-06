import StringIO
import luigi
import requests
import time
import unittest
import zipfile
from shutil import copy2

import pyproj
import shapefile
from bs4 import BeautifulSoup
from geopy import geocoders
from shapely.geometry import LineString

from app.app.services.mongodb_service import *
from build_utils import *
from luigi_extensions import ConfigurableTask


# 1.  Run unit test suite
class RunTests(ConfigurableTask):

    def output(self):
        return luigi.LocalTarget(os.path.join(self.build_config["data_repository"], "tests_complete.txt"))

    def run(self):
        suite = unittest.TestLoader().loadTestsFromName("unit_tests.TestCases")
        unittest.TextTestRunner(verbosity=2).run(suite)
        open(self.output().path,"w").close()

# 2.  Download census data
class DownloadCensusData(ConfigurableTask):

    def output(self):
        return {"census_data": luigi.LocalTarget(os.path.join(self.build_config["data_repository"], "Raw","census_data.csv")),
                "provincial_reference": luigi.LocalTarget(os.path.join(self.build_config["data_repository"], "Raw","provincial_reference.csv"))}

    def requires(self):
        return {"unit_tests": RunTests().withConfig(self.build_config)}

    def run(self):
        create_folder(self.output().path)
        # THis is the census data location as per datamap
        url = "http://www12.statcan.gc.ca/open-gc-ouvert/2016/CSV/98-400-X2016003_ENG_CSV.ZIP"
        r = requests.get(url, stream=True)
        z = zipfile.ZipFile(StringIO.StringIO(r.content))
        z.extractall(os.path.dirname(self.output()["census_data"].path))
        os.rename(os.path.join(os.path.dirname(self.output()["census_data"].path), "98-400-X2016003_English_CSV_data.csv"),self.output()["census_data"].path)
        # Copy provinical reference to data repository
        copy2("../data/provincial_reference.csv",self.output()["provincial_reference"].path)

# 3. Parse the crime data from the XML file
class ParseCrimeData(ConfigurableTask):

    def output(self):
        return {"crime_data": luigi.LocalTarget(os.path.join(self.build_config["data_repository"], "Raw","crime_data.csv"))}

    def requires(self):
        return {"unit_tests": RunTests().withConfig(self.build_config)}

    def run(self):
        create_folder(self.output()["crime_data"].path)
        # XML crime data in repository
        with open("../data/crime_data.txt","r") as f:
            txt = f.read()

        # Extract into pandas dataframe
        s = BeautifulSoup(txt,"lxml")
        # Every row has id of format id_12345
        rows = s.find_all(id=re.compile(u"id_[0-9]{4,5}"))
        d = []
        # Extract data elements from rows
        for r in rows:
            csi = r["data-score"]
            sub_element = r.find("h2")
            text = sub_element.get_text(";").split(";")
            town_name = text[0]
            province = text[1]
            d.append({"csi": csi, "town": town_name, "province": province})

        df = pandas.DataFrame.from_records(d)
        df.to_csv(self.output()["crime_data"].path, index=False, encoding="utf-8")

# 4. Scrape the school performance data from the Fraser webiste
class GetFraserSchoolData(ConfigurableTask):
    province = luigi.Parameter()

    def output(self):
        return {"school_data": luigi.LocalTarget(os.path.join(self.build_config["data_repository"], "Raw", self.province, "school_data.csv"))}

    def requires(self):
        return {"unit_tests": RunTests().withConfig(self.build_config)}

    def run(self):
        create_folder(self.output()["school_data"].path)
        # TODO: add other provinces
        urls = {"BC": {"elementary": "http://britishcolumbia.compareschoolrankings.org/elementary/SchoolsByRankLocationName.aspx",
                       "secondary": "http://britishcolumbia.compareschoolrankings.org/secondary/SchoolsByRankLocationName.aspx"}}
        prov_urls = urls[self.province]

        # Secondary
        r = requests.get(prov_urls["secondary"])
        if r.status_code != 200:
            raise Exception("Error getting Fraser school data")

        soup = BeautifulSoup(r.text,"lxml")
        tbl_secondary = parse_fraser_table(soup)
        tbl_secondary["school_level"] = "secondary"

        # Elementary
        r = requests.get(prov_urls["elementary"])
        if r.status_code != 200:
            raise Exception("Error getting Fraser school data")

        soup = BeautifulSoup(r.text,"lxml")
        tbl_elementary = parse_fraser_table(soup)
        tbl_elementary["school_level"] = "elementary"

        # Combine and output
        # TODO: GPS lookup for each school
        tbl_all = pandas.concat((tbl_secondary, tbl_elementary))
        tbl_all.to_csv(self.output()["school_data"].path, index=False, encoding="utf-8")

# 5. Get the shapefiles for the census subdivisions
class DownloadCensusShapefile(ConfigurableTask):

    def output(self):
        return {"census_shapefile": luigi.LocalTarget(os.path.join(self.build_config["data_repository"], "Raw", "lcsd000a16a_e.shp"))}

    def run(self):
        # This is the census sub-district shapefile as defined in datamap
        # TODO: make sure this url is in datamap
        url = "http://www12.statcan.gc.ca/census-recensement/2011/geo/bound-limit/files-fichiers/2016/lcsd000a16a_e.zip"
        r = requests.get(url, stream=True)
        z = zipfile.ZipFile(StringIO.StringIO(r.content))
        z.extractall(os.path.dirname(self.output()["census_shapefile"].path))


# 6. Geocode the school data using Google Maps API
class GeocodeSchoolData(ConfigurableTask):
    province = luigi.Parameter()

    def requires(self):
        return {"school_data": GetFraserSchoolData(self.province).withConfig(self.build_config)}

    def output(self):
        return {"schools_processed": luigi.LocalTarget(os.path.join(self.build_config["data_repository"], "Processed", self.province, "crime_data.pickle"))}

    def run(self):
        create_folder(self.output()["schools_processed"].path)
        # Geolocate each crime record then create a geojson object and dump to pickle
        geolocator = geocoders.GoogleV3(api_key=self.build_config["GEOCODING_API_KEY"])
        data = load_data(self.input()["school_data"]["school_data"].path)
        school_records = []
        for ix, row in data.iterrows():
            query = row["School Name"] + " School, " + row["City"] + ", " + self.province
            # Was getting weird timeouts, code to deal with it
            coords = False
            while coords == False:
                if coords is None:
                    print "Query returned empty: " + query
                    continue
                try:
                    coords = geolocator.geocode(query)
                except:
                    print "Query failed: '" + query +"', retrying"
                    time.sleep(5)

            # long, lat for GEOJSON - order important!
            d = {"location": {"type": "Point", "coordinates": [coords.longitude, coords.latitude]},
                 "town_name": row["City"],
                 "school_name": row["School Name"],
                 "school_level": row["school_level"],
                 "province": self.province,
                 "score": row["2015-16 Rating"]}
            school_records.append(d)
        save_data(school_records, self.output()["schools_processed"].path)


# 7. Geocode the crime data using Google Maps API
class GeocodeCrimeData(ConfigurableTask):

    def requires(self):
        return {"crime_data": ParseCrimeData().withConfig(self.build_config)}

    def output(self):
        return {"crime_processed": luigi.LocalTarget(os.path.join(self.build_config["data_repository"], "Processed", "crime_data.pickle"))}

    def run(self):
        create_folder(self.output()["crime_processed"].path)
        # Geolocate each crime record then create a geojson object and dump to pickle
        geolocator = geocoders.GoogleV3(api_key=self.build_config["GEOCODING_API_KEY"])
        data = load_data(self.input()["crime_data"]["crime_data"].path)
        crime_records = []
        for ix, row in data.iterrows():
            query = row["town"] + ", " + row["province"]
            # Fix for "Halifax Metropolitan Area"
            query = query.replace("Metropolitan Area","")
            # Was getting weird timeouts, code to deal with it
            coords = None
            while coords is None:
                try:
                    coords = geolocator.geocode(query)
                except:
                    print "Query failed: '" + query +"', retrying"
                    time.sleep(5)

            # long, lat for GEOJSON
            d = {"location": {"type": "Point", "coordinates": [coords.longitude,coords.latitude]},
                 "town_name": row["town"],
                 "province_name": row["province"],
                 "csi": row["csi"]}
            crime_records.append(d)
        save_data(crime_records, self.output()["crime_processed"].path)

# 8. Process the census data
class ProcessCensusData(ConfigurableTask):

    def requires(self):
        return {"census_data": DownloadCensusData().withConfig(self.build_config),
                "census_shapefile": DownloadCensusShapefile().withConfig(self.build_config)}

    def output(self):
        return {"census_processed": luigi.LocalTarget(os.path.join(self.build_config["data_repository"], "Processed", "census_data.pickle"))}

    def run(self):
        create_folder(self.output()["census_processed"].path)
        # This task takes the raw census data and the census shapefiles to produce a pickle file that can be inserted
        # into Mongo.  This pickle file will contain the geocoded census subdistricts and their associated demographic
        # data.

        # Read in the required data
        census_data = pandas.read_csv(self.input()["census_data"]["census_data"].path)
        provincial_reference = pandas.read_csv(self.input()["census_data"]["provincial_reference"].path)
        sf_reader = shapefile.Reader(self.input()["census_shapefile"]["census_shapefile"].path)
        shapes = sf_reader.shapes()
        records = sf_reader.records()

        shape_recs = []
        # Iterate over every record in the shapefile, finding the centroid and converting to lat/long
        for ix, shp in enumerate(shapes):
            d = {}
            c = LineString(shp.points).centroid
            p = pyproj.Proj(
                "+proj=lcc +lat_1=49 +lat_2=77 +lat_0=63.390675 +lon_0=-91.86666666666666 +x_0=6200000 +y_0=3000000 +ellps=GRS80 +towgs84=0,0,0,0,0,0,0 +units=m +no_defs")
            lon, lat = p(c.x, c.y, inverse=True)
            for jx, f_name in enumerate(sf_reader.fields):
                if jx == 0:
                    continue
                d[f_name[0]] = records[ix][jx - 1]
            d["lat"] = lat
            d["lon"] = lon
            shape_recs.append(d)
        df = pandas.DataFrame.from_records(shape_recs)
        df = df[["CSDUID", "CSDNAME", "PRUID", "PRNAME", "lat", "lon"]]

        # Mapping column for actual census data is "CSDUID" -> "GEO_CODE (POR)"
        # Need to create GeoJson objects for the location of each sub-district, and attach the age demographic data for
        # each district as a field of each object

        census_districts = []
        for ix, row in df.iterrows():
            # Find the entries for this subdistrict in the census data
            demo_data = census_data[census_data["GEO_CODE (POR)"] == int(row["CSDUID"])]
            # Only get age <= 18
            lens = numpy.array([len(x) for x in demo_data["DIM: Age (in single years) and average age (127)"].values])
            ix_data = (lens < 3) | (demo_data["DIM: Age (in single years) and average age (127)"] == "Under 1 year")
            demo_data = demo_data[ix_data]
            demo_data.loc[demo_data["DIM: Age (in single years) and average age (127)"] == "Under 1 year","DIM: Age (in single years) and average age (127)"] = 0
            demo_data["DIM: Age (in single years) and average age (127)"] = demo_data["DIM: Age (in single years) and average age (127)"].astype(int)
            try:
                total_population = numpy.sum(demo_data['Dim: Sex (3): Member ID: [1]: Total - Sex'].astype(int))
            except:
                # If we can't convert the population numbers to int, they are missing.  Skip this record.
                continue
            demo_data = demo_data[demo_data["DIM: Age (in single years) and average age (127)"] <= 18]
            # Create dictionary for demographic data for insertion into Mongo
            # TODO: Should do the cohort bucketing and scaling here
            demographic_dict = {"age": demo_data['DIM: Age (in single years) and average age (127)'].astype(int).values.tolist(),
                                "male_count": demo_data['Dim: Sex (3): Member ID: [2]: Male'].astype(int).values.tolist(),
                                "female_count": demo_data['Dim: Sex (3): Member ID: [3]: Female'].astype(int).values.tolist()}
            # NOTE: GEOJSON has long/lat rather than lat/long - ORDER IS IMPORTANT!
            obj = {"location":
                       {"type": "Point",
                        "coordinates": [row["lon"],row["lat"]]},
                    "subdistrict_name": row["CSDNAME"],
                    "subdistrict_id": row["CSDUID"],
                    "province_name": row["PRNAME"],
                    "province_id": row["PRUID"],
                    "age_demographics": demographic_dict,
                   "total_population": total_population}
            census_districts.append(obj)

        save_data(census_districts, self.output()["census_processed"].path)

# 9.  Build mongoDB instance
class BuildDatabase(ConfigurableTask):

    def requires(self):
        tasks = {"census_processed": ProcessCensusData().withConfig(self.build_config),
                "crime_processed": GeocodeCrimeData().withConfig(self.build_config)}

        for province in self.build_config["provinces"]:
            tasks["schools_processed_" + province] = GeocodeSchoolData(province).withConfig(self.build_config)
        return tasks

    def output(self):
        return {"mongodb_created": luigi.LocalTarget(os.path.join(self.build_config["data_repository"], "Processed", "__mongodb_created__.txt"))}

    def run(self):
        create_folder(self.output()["mongodb_created"].path)
        # Load in the processed data
        census_data = load_data(self.input()["census_processed"]["census_processed"].path)
        crime_data = load_data(self.input()["crime_processed"]["crime_processed"].path)
        # Combine school data into one table
        school_dict = {}
        for p in self.build_config["provinces"]:
            this_province = load_data(self.input()["schools_processed_" + p]["schools_processed"].path)
            # Assign province code
            for ix, el in enumerate(this_province):
                this_province[ix]["province"] = p
            school_dict[p] = this_province
        school_data = []
        for p in school_dict.keys():
            school_data = school_data + school_dict[p]

        # Hacky clean up for broken UTF-8 fields...
        for ix, el in enumerate(census_data):
            census_data[ix]["province_name"] = el["province_name"].split("/")[0]
            census_data[ix]["subdistrict_name"] = el["subdistrict_name"].decode("utf-8", errors="ignore")

        # Hacky clean up for flipped lat/long in geojson -
        # TODO: ERROR HAS BEEN FIXED UPSTREAM, REMOVE ON NEXT RUN!
        for ix, el in enumerate(census_data):
            c = el["location"]["coordinates"]
            new_c = [c[1], c[0]]
            census_data[ix]["location"]["coordinates"] = new_c
        for ix, el in enumerate(crime_data):
            c = el["location"]["coordinates"]
            new_c = [c[1], c[0]]
            crime_data[ix]["location"]["coordinates"] = new_c
        for ix, el in enumerate(school_data):
            c = el["location"]["coordinates"]
            new_c = [c[1], c[0]]
            school_data[ix]["location"]["coordinates"] = new_c

        # POPULATE DB FOR TESTING
        # TODO: Add TRAFFIC!!
        mg_drop("census")
        mg_drop("crime")
        mg_drop("schools")
        mg_save(census_data, "census")
        mg_save(crime_data, "crime")
        mg_save(school_data, "schools")

        # Add indexes
        mg_create_geo_index("census", "location")
        mg_create_geo_index("crime", "location")
        mg_create_geo_index("schools", "location")


        open(self.output()["mongodb_created"].path,"w").close()

        # TODO: Do I make it robust enough to deploy on another machine?  Probably.



