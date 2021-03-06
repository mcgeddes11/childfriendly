import sys, yaml, hashlib, json, os, logging, luigi
from shutil import copy2
from build_utils import create_folder
from datetime import datetime
from tasks import RunTests, DownloadCensusData, ParseCrimeData, DownloadCensusShapefile, GetFraserSchoolData, ProcessCensusData, GeocodeCrimeData, GeocodeSchoolData, BuildDatabase, ParseBcTrafficData



if __name__ == "__main__":

    if len(sys.argv) < 2:
        raise Exception("No config path file, exiting")
    else:
        configPath = sys.argv[1]

    # # Load config
    with open(configPath, 'r') as stream:
        config = yaml.load(stream)

    # Set up logging
    log_level = eval("logging." + config["log_level"])
    formatter = logging.Formatter(fmt='%(asctime)s - %(levelname)s - %(module)s - %(message)s')
    file_handler = logging.FileHandler(os.path.join(config["data_repository"], "process_log.log"))
    file_handler.setFormatter(formatter)
    file_handler.setLevel(log_level)
    logger = logging.getLogger('luigi-interface')
    logger.setLevel(log_level)
    logger.addHandler(file_handler)

    # Create geocoder object
    config["GEOCODING_API_KEY"] = os.getenv("google_maps_key")


    #  Add tasks to luigi_jobs build/job
    tasks = []
    tasks.append(RunTests().withConfig(config))
    tasks.append(DownloadCensusData().withConfig(config))
    tasks.append(DownloadCensusShapefile().withConfig(config))
    tasks.append(ParseCrimeData().withConfig(config))
    tasks.append(ProcessCensusData().withConfig(config))
    tasks.append(GeocodeCrimeData().withConfig(config))
    for province in config["provinces"]:
        # Traffic
        if province == "BC":
            tasks.append(ParseBcTrafficData().withConfig(config))
        tasks.append(GetFraserSchoolData(province).withConfig(config))
        tasks.append(GeocodeSchoolData(province).withConfig(config))
    tasks.append(BuildDatabase().withConfig(config))




    luigi.build(tasks, local_scheduler=True, workers=config["luigi_worker_count"])