import syslog
from flask import Flask, request, render_template, send_from_directory
from flask.ext.bootstrap import Bootstrap
import json
import re

from datetime import timedelta
from flask import make_response, request, current_app
from functools import update_wrapper
import sstoreclient
import requests

app = Flask(__name__)
app.config.setdefault('BOOTSTRAP_SERVE_LOCAL',True)
bootstrap = Bootstrap(app)

# Set debug mode.
debug = False

# Create S-Store client object instance
db = sstoreclient.sstoreclient()
apiurl = 'http://localhost'

# ================
# REST API function definitions
# ================

# Logins
# ========

# User registration
# ---------
# Verb:      POST
# Route:     /REST/1.0/login/signup
# Form data: <string:first_name>,<string:last_name>
# Response:  {<int:USER_ID>}
@app.route('/REST/1.0/login/signup', methods=['POST'])
def user_signup():
    proc = 'SignUpName'
    fname = request.form['first_name']
    lname = request.form['last_name']
    args = [fname,lname]
    try:
        # Get data from S-Store.
        data = db.call_proc(proc,args)
    # Failure cases
    except Exception as e:
        # Client failed to connect to or get data from S-Store.
        log_procerr(proc,str(e))
        return '{}', 500
    if not data['success']:
        # DB procedure execution failed.
        log_procerr(proc,str(data['error']))
        return '{}', 500
    # Success case
    else:
        users = data['data']
        return json.dumps(users[0])

# User login
# ---------
# Verb:      POST
# Route:     /REST/1.0/login/check
# Form data: <string:user_name>
# Response:  {<int:USER_ID>}
@app.route('/REST/1.0/login/check', methods=['POST'])
def check_login():
    proc = 'FindUser'
    args = [request.form['user_name']]
    try:
        # Get data from S-Store.
        data = db.call_proc(proc,args)
    # Failure cases
    except Exception as e:
        # Client failed to connect to or get data from S-Store.
        log_procerr(proc,str(e))
        return '{}', 500
    if not data['success']:
        # DB procedure execution failed.
        log_procerr(proc,str(data['error']))
        return '{}', 500
    # Success case
    else:
        # TODO: Figure out what makes sense in the schema to use as a unique
        # token for login purposes.
        users = data['data']
        if len(users) > 0:
            return json.dumps(subdict(data['data'][0],'USER_ID'))
        else:
            return '{}', 404

# Stations
# =========

# Get nearby stations
# ---------
# Verb:     GET
# Route:    /REST/1.0/stations/all
# Response: [{<int:STATION_ID>, <string:STATION_NAME>, <int:LATITUDE>,
#             <int:LONGITUDE>, <string:STREET_ADDRESS>}, ...]
@app.route('/REST/1.0/stations/all')
def all_stations():
    proc = 'Stations'
    try:
        data = db.call_proc(proc)
    except Exception as e:
        log_procerr(proc,str(e))
        return '{}', 500
    return json.dumps(data['data'])

# Verb:     GET
# Route:    /REST/1.0/stations/all/<float:lat>/<float:lon>/<float:rad>
# Response: [{<int:STATION_ID>, <string:STATION_NAME>, <int:LATITUDE>,
#             <int:LONGITUDE>, <string:STREET_ADDRESS>}, ...]
@app.route('/REST/1.0/stations/all/<float:lat>/<float:lon>/<float:rad>')
def all_stations_in_rad(lat, lon, rad):
    return all_stations()

# Get individual station info
# ---------
# Verb:     GET
# Route:    /REST/1.0/stations/info/<int:station_id>
# Response: {<int:STATION_ID>,<string:STATION_NAME>,<string:STREET_ADDRESS>,
#            <int:LATITUDE>,<int:LONGITUDE>,<int:CURRENT_BIKES>,
#            <int:CURRENT_DOCKS>,<int:CURRENT_DISCOUNT>
@app.route('/REST/1.0/stations/info/<int:station_id>')
def stations_info(station_id):
    proc = 'GetStationStatus'
    args = [station_id]
    try:
        # Get data from S-Store.
        data = db.call_proc(proc,args)
    # Failure cases
    except Exception as e:
        # Client failed to connect to or get data from S-Store.
        log_procerr(proc,str(e))
        return '{}', 500
    if not data['success']:
        # DB procedure execution failed.
        log_procerr(proc,str(data['error']))
        return '{}', 500
    # Success case
    else:
        stations = data['data']
        if len(stations) > 0:
            return json.dumps(stations[0])
        else:
            return '{}', 404

# Bikes
# ========

# Get current bike positions
# ---------
# Verb:     GET
# Route:    /REST/1.0/bikes/active
# Response: [ {<int:USER_ID>,<float:LATITUDE>,<float:LONGITUDE>}, ... ]
@app.route('/REST/1.0/bikes/active')
def active_bikes():
    proc = 'UserLocations'
    try:
        # Get data from S-Store.
        data = db.call_proc(proc)
    # Failure cases
    except Exception as e:
        # Client failed to connect to or get data from S-Store.
        log_procerr(proc,str(e))
        return '{}', 500
    if not data['success']:
        # DB procedure execution failed.
        log_procerr(proc,str(data['error']))
        return '{}', 500
    # Success case
    else:
        return json.dumps(data['data'])
# Verb:     GET
# Route:    /REST/1.0/bikes/active/<float:lat>/<float:lon>/<float:rad>
# Response: [ {<int:USER_ID>,<float:LATITUDE>,<float:LONGITUDE>}, ... ]
@app.route('/REST/1.0/bikes/active/<float:lat>/<float:lon>/<float:rad>')
def active_bikes_in_rad(lat, lon, rad):
    return active_bikes()

# Get individual bike info
# ---------
# Verb:     GET
# Route:    /REST/1.0/bikes/info/<int:user_id>
# Response: {<int:USER_ID>,<float:LATITUDE>,<float:LONGITUDE>}
@app.route('/REST/1.0/bikes/info/<int:user_id>')
def bike_info(user_id):
    proc = 'GetBikeStatus'
    args = [user_id]
    try:
        # Get data from S-Store.
        data = db.call_proc(proc,args)
    # Failure cases
    except Exception as e:
        # Client failed to connect to or get data from S-Store.
        log_procerr(proc,str(e))
        return '{}', 500
    if not data['success']:
        # DB procedure execution failed.
        log_procerr(proc,str(data['error']))
        return '{}', 500
    # Success case
    else:
        bikedata = data['data']
        if len(bikedata) > 0:
            return json.dumps(bikedata[0])
        else:
            return '{}', 404

# Checkout bike
# ---------
# Verb:      POST
# Route:     /REST/1.0/bikes/checkout
# Form data: <int:station_id>,<int:user_id>
# Response:  Success (200)
#            Failure (401) - User does not exist
#            Failure (403) - User already has a bike checked out
#            Failure (503) - No bikes available at station
@app.route('/REST/1.0/bikes/checkout', methods=['POST'])
def checkout_bike():
    proc = 'CheckoutBike'
    user = int(request.form['user_id'])
    station = int(request.form['station_id'])
    args = [user, station]
    try:
        # Get data from S-Store.
        data = db.call_proc(proc,args)
    # Failure cases
    except Exception as e:
        # Client failed to connect to or get data from S-Store.
        log_procerr(proc,str(e))
        return '{}', 500
    if not data['success']:
        # DB procedure execution failed.
        nouserstr = 'Rider: ' + str(user) + ' does not exist'
        alreadystr = 'Rider: ' + str(user) + ' already has a bike checked out'
        nobikestr = 'Rider: ' + str(user) + ' was unable to checkout a bike'
        if re.search(nouserstr,data['error']):
            return '{}', 401 # Unauthorized
        elif re.search(alreadystr,data['error']):
            return '{}', 403 # Forbidden
        elif re.search(nobikestr,data['error']):
            return '{}', 503 # Service Unavailable
        else:
            log_procerr(proc,str(data['error']))
            return '{}', 500
    # Success case
    else:
        return json.dumps(data['data'])

# Checkin bike
# ---------
# Verb:      POST
# Route:     /REST/1.0/bikes/checkin
# Form data: <int:station_id>,<int:user_id>
# Response:  Success (200)
#            Failure (401) - User does not exist
#            Failure (403) - User does not have a bike to checkin
#            Failure (503) - No docks available at station
@app.route('/REST/1.0/bikes/checkin', methods=['POST'])
def checkin_bike():
    proc = 'CheckinBike'
    user = int(request.form['user_id'])
    station = int(request.form['station_id'])
    args = [user, station]
    try:
        # Get data from S-Store.
        data = db.call_proc(proc,args)
    # Failure cases
    except Exception as e:
        # Client failed to connect to or get data from S-Store.
        log_procerr(proc,str(e))
        return '{}', 500
    if not data['success']:
        # DB procedure execution failed.
        nouserstr = 'Rider: ' + str(user) + ' does not exist'
        nobikestr = 'Rider ' + str(user) + ' does not have a bike checked out'
        nodockstr = 'Rider: ' + str(user) + ' was unable to checkin a bike'
        if re.search(nouserstr,data['error']):
            return '{}', 401 # Unauthorized
        elif re.search(nobikestr,data['error']):
            return '{}', 403 # Forbidden
        elif re.search(nodockstr,data['error']):
            return '{}', 503 # Service Unavailable
        else:
            log_procerr(proc,str(data['error']))
            return '{}', 500
    # Success case
    else:
        return json.dumps(data['data'])

# Send recent bike positional data
# ---------
# Verb:      POST
# Route:     /REST/1.0/bikes/pos
# Form data: <int:user_id>,<float:lat>,<float:lon>
# Response:  Success (200)
#            Failure (401) - User does not exist
@app.route('/REST/1.0/bikes/pos', methods=['POST'])
def send_bike_position():
    proc = 'RideBike'
    user = int(request.form['user_id'])
    lat = float(request.form['lat'])
    lon = float(request.form['lon'])
    args = [user, lat, lon]
    try:
        # Get data from S-Store.
        data = db.call_proc(proc, args)
    # Failure cases
    except Exception as e:
        # Client failed to connect to or get data from S-Store.
        log_procerr(proc, str(e)) 
        return '{}', 500
    if not data['success']:
        # DB procedure execution failed.
        nouserstr = 'Rider: ' + str(user) + ' does not exist'
        nobikestr = 'Rider: ' + str(user) + ' does not have a bike checked out'
        if re.search(nouserstr,data['error']):
            return '{}', 401 # Unauthorized
        elif re.search(nobikestr,data['error']):
            return '{}', 403 # Forbidden
        else:
            log_procerr(proc,str(data['error']))
            return '{}', 500
    # Success case
    else:
        return json.dumps(data['data'])

# Other API functions
# ========

# Get general statistics
# ---------
# Verb:     GET
# Route:    /REST/1.0/stats
# Response: {<int:BIKES>,<int:ACTIVE_BIKES>,<int:STATIONS>,<int:USERS>,
#            <int:BIKES_PER_STATION}
@app.route('/REST/1.0/stats')
def get_stats():
    stats = dict()
    stats['BIKES'], stats['ACTIVE_BIKES'] = get_bikestats()
    stats['STATIONS'] = get_stationstats()
    stats['USERS'] = get_userstats()
    stats['BIKES_PER_STATION'] = stats['BIKES'] // stats['STATIONS']
    return json.dumps(stats)

# Get statistics about bikes.
def get_bikestats():
    proc = 'Bikes'
    try:
        # Get data from S-Store.
        data = db.call_proc(proc)
    # Failure cases
    except Exception as e:
        # Client failed to connect to or get data from S-Store.
        log_procerr(proc,str(e))
        return '?'
    if not data['success']:
        # DB procedure execution failed.
        log_procerr(proc,str(data['error']))
        return '?'
    # Success case
    else:
        bikes = data['data']
        active = 0
        for bike in bikes:
            if bike['CURRENT_STATUS'] == 2:
                active = active + 1
        return len(data['data']), active

# Get statistics about stations.
def get_stationstats():
    proc = 'Stations'
    try:
        # Get data from S-Store.
        data = db.call_proc(proc)
    # Failure cases
    except Exception as e:
        # Client failed to connect to or get data from S-Store.
        log_procerr(proc,str(e))
        return '?'
    if not data['success']:
        # DB procedure execution failed.
        log_procerr(proc,str(data['error']))
        return '?'
    # Success case
    else:
        return len(data['data'])

# Get statistics about users.
def get_userstats():
    proc = 'Users'
    try:
        # Get data from S-Store.
        data = db.call_proc(proc)
    # Failure cases
    except Exception as e:
        # Client failed to connect to or get data from S-Store.
        log_procerr(proc,str(e))
        return '?'
    if not data['success']:
        # DB procedure execution failed.
        log_procerr(proc,str(data['error']))
        return '?'
    # Success case
    else:
        return len(data['data'])

# Helper function. Extracts and returns only the set of key/value pairs that
# we want from a given dict.
def subdict(d, keys):
    d2 = dict()
    for k, v in d.iteritems():
        if k in keys:
            d2[k] = v
    return d2

def log_procerr(proc = '', msg = ''):
    err = 'Exception encountered when calling S-Store procedure "'
    err += proc + '": ' + msg
    syslog.syslog(syslog.LOG_ERR, err)
    return

# ================
# Main app function definitions
# ================

# This is a GET route to display the "view all stations" page
@app.route('/stations')
def view_all_stations():
    return render_template('stations.html')

# This is a GET route to display the "view all bikes" page
@app.route('/bikes')
def view_all_bikes():
    return render_template('bikes.html')

# This is a GET route to display the "view all riders" page
@app.route('/users')
def view_all_riders():
    return render_template('users.html')

# This is a GET route to display the landing page of bikeshare
@app.route('/')
def home():
    apiroute = '/REST/1.0/stats'
    r = requests.get(apiurl + apiroute)
    if r.status_code == 200:
        data = r.json()
        return render_template('index.html', bikes=data['BIKES'],
            active_bikes = data['ACTIVE_BIKES'], stations=data['STATIONS'],
            users=data['USERS'], bikes_per_station=data['BIKES_PER_STATION'])
    else:
        return render_template('index.html')

# This is a GET route to display a single bike page of a given name
@app.route('/bike/<int:bike_id>')
def view_bike(bike_id):
    return render_template('bike.html',bike_id=bike_id)

# This is a GET route to display a single station page of a given name
@app.route('/station/<int:station_id>')
def view_station(station_id):
    return render_template('station.html',station_id=station_id)

# This is a GET route to display a single user page of a given name
@app.route('/user/<int:user_id>')
def view_user(user_id):
    return render_template('user.html',user_id=user_id)

@app.route('/javascript/<path:path>', methods=['GET','OPTIONS'])
def js_proxy(path):
    return send_from_directory(app.root_path + '/javascript/', path)

@app.errorhandler(404)
def page_not_found(e):
    if re.match('/REST',request.path):
        return '{}', 404
    else:
        return render_template('404.html'), 404

@app.errorhandler(500)
def internal_server_error(e):
    if re.match('/REST',request.path):
        return '{}', 500
    else:
        return render_template('500.html'), 500

if __name__ == '__main__':
    if debug:
        app.run(host='127.0.0.1', port=8081, debug=True)
    else:
        app.run(host='0.0.0.0', port=8081, debug=False)

