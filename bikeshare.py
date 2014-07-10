import syslog
from flask import Flask, request, render_template, send_from_directory
from flask.ext.bootstrap import Bootstrap
import json
import re

from datetime import timedelta
from flask import make_response, request, current_app
from functools import update_wrapper
import sstoreclient

app = Flask(__name__)
app.config.setdefault('BOOTSTRAP_SERVE_LOCAL',True)
bootstrap = Bootstrap(app)

# Set debug mode.
debug = False

# Create S-Store client object instance
db = sstoreclient.sstoreclient()

# ================
# REST API function definitions
# ================

# Logins
# ========

# User login
# ---------
# Verb:      POST
# Route:     /REST/1.0/login/check
# Form data: <string:user_name>
# Response:  {<int:user_id>}
@app.route('/REST/1.0/login/check', methods=['POST'])
def check_login():
    db = open('data/users.json','r')
    data = json.load(db)
    target_user = request.form['user_name']
    for u in data:
        if u['user_name'] == target_user:
            return json.dumps(subdict(u, ['user_id']), ensure_ascii=True)
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
    proc = 'TestProcedure'
    try:
        data = db.call_proc(proc)
        return json.dumps(data['data'])
    except Exception as e:
        log_procerr(proc,str(e))
        return '{}', 500

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
# Response: {<int:num_bikes>,<int:num_docks>,<string:address>,<float:price>}
@app.route('/REST/1.0/stations/info/<int:station_id>')
def stations_info(station_id):
    s = '/home/dramage/bikeshare-web/data/station_' + str(station_id) + '.json'
    print s
    try:
        db = open(s,'r')
    except IOError:
        return '{}', 404
    data = json.load(db)
    return json.dumps(data, ensure_ascii=True)

# Bikes
# ========

# Get current bike positions
# ---------
# Verb:     GET
# Route:    /REST/1.0/bikes/active
# Response: [ {<int:bike_id>,<float:lat>,<float:lon>}, ... ]
@app.route('/REST/1.0/bikes/active')
def active_bikes():
    db = open('data/bikes.json','r')
    data = json.load(db)
    return json.dumps(data, ensure_ascii=True)
# Verb:     GET
# Route:    /REST/1.0/bikes/active/<float:lat>/<float:lon>/<float:rad>
# Response: [ {<int:bike_id>,<float:lat>,<float:lon>}, ... ]
@app.route('/REST/1.0/bikes/active/<float:lat>/<float:lon>/<float:rad>')
def active_bikes_in_rad(lat, lon, rad):
    return active_bikes()

# Get individual bike info
# ---------
# Verb:     GET
# Route:    /REST/1.0/bikes/info/<int:bike_id>
# Response: {<float:lat>,<float:lon>,<float:distance>,<int:time>,
#            <[ string, ... ]:reports>}
@app.route('/REST/1.0/bikes/info/<int:bike_id>')
def bike_info(bike_id):
    s = 'data/bike_' + str(bike_id) + '.json'
    try:
        db = open(s,'r')
    except IOError:
        return '{}', 404
    data = json.load(db)
    return json.dumps(data, ensure_ascii=True)

# Checkout bike
# ---------
# Verb:      POST
# Route:     /REST/1.0/bikes/checkout
# Form data: <int:station_id>,<int:user_id>
# Response:  Success (200) / Failure (403)
@app.route('/REST/1.0/bikes/checkout', methods=['POST'])
def checkout_bike():
    proc = 'CheckoutBike'
    target_user = int(request.form['user_id'])
    target_station = int(request.form['station_id'])
    args = [target_user, target_station]
    try:
        data = db.call_proc(proc, args)
        if data['success']:
            return json.dumps(data['data'])
        else:
            return json.dumps(data['data']), 403
    except Exception as e:
        log_procerr(proc, str(e)) 
        return '{}', 500

# Checkin bike
# ---------
# Verb:      POST
# Route:     /REST/1.0/bikes/checkin
# Form data: <int:station_id>,<int:user_id>
# Response:  Success (200) / Failure (403)
@app.route('/REST/1.0/bikes/checkin', methods=['POST'])
def checkin_bike():
    proc = 'CheckinBike'
    target_user = int(request.form['user_id'])
    target_station = int(request.form['station_id'])
    args = [target_user, target_station]
    try:
        data = db.call_proc(proc, args)
        if data['success']:
            return json.dumps(data['data'])
        else:
            return json.dumps(data['data']), 403
    except Exception as e:
        log_procerr(proc, str(e)) 
        return '{}', 500

# Get/send recent bike positional data
# ---------
# Verb:     GET
# Route:    /REST/1.0/bikes/pos/<int:bike_id>
# Response: [ {<float:lat>,<float:lon>,<int:time>}, ... ]
@app.route('/REST/1.0/bikes/pos/<int:bike_id>')
def get_bike_position(bike_id):
    s = 'data/bikepos_' + str(bike_id) + '.json'
    try:
        db = open(s,'r')
    except IOError:
        return '{}', 404
    data = json.load(db)
    return json.dumps(data, ensure_ascii=True)
# Verb:      POST
# Route:     /REST/1.0/bikes/pos
# Form data: <int:user_id>,<float:lat>,<float:lon>
# Response:  Success (200) / Failure (403)
@app.route('/REST/1.0/bikes/pos', methods=['POST'])
def send_bike_position():
    proc = 'RideBike'
    user = int(request.form['user_id'])
    lat = float(request.form['lat'])
    lon = float(request.form['lon'])
    args = [user, lat, lon]
    try:
        data = db.call_proc(proc, args)
        if data['success']:
            return json.dumps(data['data'])
        else:
            return json.dumps(data['data']), 403
    except Exception as e:
        log_procerr(proc, str(e)) 
        return '{}', 500

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
    return render_template('index.html')

# This is a GET route to display a single bike page of a given name
@app.route('/bike/<int:bike_id>')
def view_bike(bike_id):
    return render_template('bikes.html',bike_id=bike_id)

# This is a GET route to display a single station page of a given name
@app.route('/station/<int:statio_id>')
def view_station(station_id):
    return render_template('stations.html',station_id=station_id)

# This is a GET route to display a single user page of a given name
@app.route('/user/<int:user_id>')
def view_user(user_id):
    return render_template('users.html',user_id=user_id)

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
        app.run(host='127.0.0.1', port=8089, debug=True)
    else:
        app.run(host='0.0.0.0', port=8089, debug=False)

