import os, re, json, pandas, pickle

# Utility function for creating folders for output
def create_folder(fileName):
    dirName = os.path.dirname(fileName)
    print(dirName)
    if not os.path.exists(dirName):
        os.makedirs(dirName)

def load_data(pathname):
    if pathname.endswith(".pickle"):
        with open(pathname,"rb") as f:
            d = pickle.load(f)
    elif pathname.endswith(".csv"):
        d = pandas.read_csv(pathname)
    return d

def save_data(data_object, pathname, protocol=2):
    if pathname.endswith(".pickle"):
        with open(pathname,"wb") as f:
            pickle.dump(data_object,f,protocol=protocol)
    elif pathname.enswith(".csv") and type(data_object) == pandas.DataFrame:
        data_object.to_csv(pathname, index=False)

