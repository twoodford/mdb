# mdb._weatherparse
# Fetch weather from various online sources
# Code disclaimer: This stuff has low standards.  Web scraping is a hackish thing in general.

from bs4 import BeautifulSoup
import datetime
import email.utils
import sqlite3
import urllib.request
import xml.sax
import xml.sax.handler

class _WundergroundHandler(xml.sax.handler.ContentHandler):
    state = None
    obsdata = {}
    def __init__(self, dbconn, debug=False):
        self.conn = dbconn
        self.debug = debug

    def startElement(self, name, attrs):
        self.state = name
    
    def characters(self, ch):
        if self.state is not None:
            self.obsdata[self.state] = ch

    def endElement(self, name):
        if name=="current_observation":
            self._finalize_obs()
        self.state = None

    def _finalize_obs(self):
        if self.debug:
            print("DEBUG: "+str(self.obsdata["observation_time_rfc822"]))
            print("DEBUG: temp_c="+self.obsdata["temp_c"])
            print("DEBUG: pressure_mb="+self.obsdata["pressure_mb"])
            print("DEBUG: precip_1hr="+self.obsdata["precip_1hr_metric"])
        tm_1 = email.utils.parsedate_tz(self.obsdata["observation_time_rfc822"])
        if tm_1 is None: return # Couldn't parse date
        tm = datetime.datetime.fromtimestamp(email.utils.mktime_tz(tm_1))
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM basic_weather WHERE time=?", (tm.timestamp(),))
        if len(cur.fetchall()) < 0: # cur.rowcount doesn't seem to work for this
            temp_c = float(self.obsdata["temp_c"])
            pressure = float(self.obsdata["pressure_mb"])
            precip = float(self.obsdata["precip_1hr_metric"].split(" ")[0])
            cur.execute('''INSERT INTO basic_weather VALUES (?,?,?,?)''', (tm.timestamp(), temp_c, pressure, precip))
            self.conn.commit()
            self.obsdata={}
        elif self.debug:
            print("DEBUG: WU Already recorded, skipping")

def _parse_wunderground_xml(inxml, db):
    "Add new Weather Underground data from the XML string to the given database"
    parser = xml.sax.parse(inxml, _WundergroundHandler(db))

def _parse_nws_html(inxml, db):
    "Add new NWS data from the XML string to the database"
    soup = BeautifulSoup(inxml, "html.parser")
    # datetime parsing setup
    cutoff_day = datetime.datetime.now().day
    current_mo = datetime.datetime.now().month
    current_yr = datetime.datetime.now().year
    # get a cursor
    cur = db.cursor()
    for row in soup.find_all("tr"):
        cells = row.find_all("td")
        if len(cells) == 18:
            try:
                day_of_month = cells[0].string
                time = cells[1].string
                wind = cells[2].string.split(" ")
                conditions = cells[4].string
                sky_cond = [(s[:3], s[3:]) for s in cells[5].string.split(" ")]
                def _percentage_key(x):
                    # Convert x[1] to an int, or return 0 otherwise
                    try:
                        return int(x[1])
                    except ValueError:
                        return 0
                sky_cond.sort(key=_percentage_key, reverse=True)
                simple_cond = _simplify_conditions(conditions)
                dt = _infer_datetime(cutoff_day, current_mo, current_yr, day_of_month, time)
                if wind[0] == "Calm" or wind[0] == "NA":
                    wind.append(0)
                #DBG print("DEBUG: "+str(dt)+": "+str(wind)+" "+conditions+" "+simple_cond+" "+str(sky_cond))
                cur.execute("SELECT * FROM nws_weather WHERE time=?", (dt.timestamp(),))
                if len(cur.fetchall()) > 0: # cur.rowcount doesn't seem to work for this
                    continue

                if sky_cond[0][1] == '':
                    cloud_cover = 0 # Handle blank strings (occur on clear days)
                else:
                    cloud_cover = float(sky_cond[0][1])/10

                cur.execute("INSERT INTO nws_weather VALUES (?,?,?,?,?)", 
                    (dt.timestamp(), sky_cond[0][0], cloud_cover, simple_cond, int(wind[1])))
            except ValueError as e:
                print("ValueError during parsing, continuing")
    db.commit()

def _simplify_conditions(conditions):
    "Convert a NWS weather description string to a set of simple classifications"
    if conditions.find("Snow") != -1:
        return "snow"
    elif conditions.find("Rain") != -1:
        return "rain"
    elif conditions.find("Overcast") != -1:
        return "white"
    elif conditions.find("Fog") != -1:
        return "white"
    elif conditions.find("Mist") != -1:
        return "white"
    elif conditions.find("Few Clouds") != -1:
        return "sunny"
    elif conditions.find("Mostly Cloudy") != -1 or conditions == "Cloudy":
        return "clouds"
    elif conditions.find("Partly Cloudy") != -1:
        return "sunny"
    elif conditions.find("Clear") != -1:
        return "sunny"
    else:
        return "?"

def _infer_datetime(cutoff_day, current_mo, current_yr, dom_str, time_str):
    day = int(dom_str)
    year = current_yr
    if day > cutoff_day:
        month = current_mo - 1
        if month == 0:
            # Move back to previous year
            month = 12
            year = current_yr - 1
    else:
        month = current_mo
    time_split = time_str.split(":")
    return datetime.datetime(year, month, day, int(time_split[0]), int(time_split[1]))

def add_wunderground_data(station_name, db):
    xml_file = urllib.request.urlopen( \
            "http://api.wunderground.com/weatherstation/WXDailyHistory.asp?ID={0}&format=XML".format(station_name))
    _parse_wunderground_xml(xml_file, db)

def add_nws_data(station_name, db):
    xml_file = urllib.request.urlopen("http://w1.weather.gov/data/obhistory/{0}.html".format(station_name))
    _parse_nws_html(xml_file, db)
