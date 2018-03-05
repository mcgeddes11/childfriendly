import os, re, json, pandas, pickle, numpy

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

def parse_fraser_table(soup):
    # find table elements
    tbls = soup.find_all("table")
    # Find table element with most elements
    lens = numpy.array([len(x) for x in tbls])
    max_len = numpy.max(lens)
    tbl_recs = []
    # Find table in question
    for rec in tbls:
        if len(rec) == max_len:
            d = {}
            # FInd all rows
            rows = rec.find_all("tr")
            # Loop over rows
            for ix, row in enumerate(rows):
                tds = row.find_all("td")
                # If ix == 0, we have the header row
                if ix == 0:
                    headers = [x.text for x in tds] + ["report_card_link"]
                else:
                    this_row = []
                    for val in tds:
                        txt = val.text
                        href = val.find("a")
                        if href and "compare" not in txt:
                            href_report = href["href"]
                        this_row.append(txt)
                    this_row.append(href_report)

                    tbl_recs.append(this_row)
    # Put data in dataframe
    recs = []
    for rec in tbl_recs:
        r = {}
        for ix, k in enumerate(headers):
            r[k] = rec[ix]
        recs.append(r)
    data = pandas.DataFrame.from_records(recs)
    # Rename and remove shitty column
    new_cols = [x.split(":")[0] for x in data.columns]
    data.columns = new_cols
    del data["Schools found"]
    return data

