from configs.configs import Config
import requests
import urllib2
import zipfile
from ingestion.download import Loader, FileItem
from constants import RAW_FILE_PREFIX
import xml.etree.ElementTree
import logging
from dateutil import parser
import bs4
import pandas as pd
from StringIO import StringIO
import os
from io import BytesIO


def state_download(state):
    config_file = Config.config_file_from_state(state=state)
    configs = Config(file_name=config_file)

    if state == "north_carolina":
        today = nc_date_grab()
        list_files = configs['data_chunk_links']
        zipped_files = []
        for i, url in enumerate(list_files):
            target_path = "/tmp/" + state + str(i) + ".zip"
            zipped_files.append(target_path)
            response = requests.get(url, stream=True)
            handle = open(target_path, "wb")
            for chunk in response.iter_content(chunk_size=512):
                if chunk:  # filter out keep-alive new chunks
                    handle.write(chunk)
            handle.close()
        file_to_zip = today + ".zip"
        with zipfile.ZipFile(file_to_zip, 'w') as myzip:
            for f in zipped_files:
                myzip.write(f)
        file_to_zip = FileItem("NC file auto download", filename=file_to_zip)
        loader = Loader(config_file=config_file, force_date=today,
                        clean_up_tmp_files=False)
        loader.s3_dump(file_to_zip, file_class=RAW_FILE_PREFIX)

    elif state == "ohio":
        today = str(ohio_get_last_updated().isoformat())[0:10]
        list_files = configs['data_chunk_links']
        zipped_files = []
        for i, url in enumerate(list_files):
            logging.info("downloading {} file".format(url))
            target_path = "/tmp/" + state + str(i) + ".txt.gz"
            zipped_files.append(target_path)
            response = requests.get(url, stream=True, verify=False)
            handle = open(target_path, "wb")
            for chunk in response.iter_content(chunk_size=512):
                if chunk:
                    handle.write(chunk)
            handle.close()
            if i == 0:
                logging.info("reading in file {}".format(url))
                df = pd.read_csv(target_path)
                os.remove(target_path)
            else:
                logging.info("reading in file {}".format(url))
                new_df = pd.read_csv(target_path)
                os.remove(target_path)
                df = pd.concat([df, new_df], axis=0)
        logging.info("reading finished, creating file item and uploading")
        file_name = today + ".csv.gz"
        df.to_csv(file_name, compression='gzip')

        file_final = FileItem("OH file auto download", filename=file_name)
        loader = Loader(config_file=config_file, force_date=today,
                        clean_up_tmp_files=False)
        loader.s3_dump(file_item=file_final)


def nc_date_grab():
    nc_file = urllib2.urlopen(
        'https://s3.amazonaws.com/dl.ncsbe.gov?delimiter=/&prefix=data/')
    data = nc_file.read()
    nc_file.close()
    root = xml.etree.ElementTree.fromstring(data)

    def nc_parse_xml(file_name):
        for child in root:
            if "Contents" in child.tag:
                z = 0
                for i in child:
                    if file_name in i.text:
                        z += 1
                        continue
                    if z == 1:
                        return i.text

    file_date_vf = nc_parse_xml(file_name="data/ncvoter_Statewide.zip")
    file_date_his = nc_parse_xml(file_name="data/ncvhis_Statewide.zip")

    if file_date_his[0:10] != file_date_vf[0:10]:
        logging.info(
            "Different dates between files, reverting to voter file date")

    file_date_vf = parser.parse(file_date_vf).isoformat()
    return file_date_vf

def ohio_get_last_updated():

    html = requests.get("https://www6.sos.state.oh.us/ords/f?p=VOTERFTP:STWD",
                        verify=False).text
    soup = bs4.BeautifulSoup(html, "html.parser")
    results = soup.find_all("td", {"headers": "DATE_MODIFIED"})
    return max(parser.parse(a.text) for a in results)
