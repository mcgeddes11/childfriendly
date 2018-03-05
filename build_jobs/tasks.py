import copy, logging, pickle, unittest, luigi, sys, requests, zipfile, StringIO, re, pandas
from build_utils import *
from shutil import copy2
from bs4 import BeautifulSoup

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

        s = BeautifulSoup(txt,"lxml")
        rows = s.find_all(id=re.compile(u"id_[0-9]{4,5}"))
        d = []
        for r in rows:
            csi = r["data-score"]
            sub_element = r.find("h2")
            text = sub_element.get_text(";").split(";")
            town_name = text[0]
            province = text[1]
            d.append({"csi": csi, "town": town_name, "province": province})

        df = pandas.DataFrame.from_records(d)
        df.to_csv(self.output()["crime_data"].path, index=False, encoding="utf-8")


