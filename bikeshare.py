import syslog
from flask import Flask, request, render_template, send_from_directory, jsonify
from flask.ext.bootstrap import Bootstrap
import json
import re
import os

from datetime import timedelta
from flask import make_response, request, current_app
from functools import update_wrapper

app = Flask(__name__)

bootstrap = Bootstrap(app)

# Set debug mode.
debug = True

#load simulated routes
routes = []
riderId = 0
for filename in os.listdir('/home/dramage/bikeshare-web/data/routes'):
    routeFile = open('/home/dramage/bikeshare-web/data/routes/' + filename, 'r')
    routes.append({ 'routeIndex' : 0, 'route' : json.load(routeFile)})
    routeFile.close()

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
# Response: [ {<int:station_id>,<float:lat>,<float:lon>,<string:address>}, ... ]
@app.route('/REST/1.0/stations/all')
def all_stations():
    try:
        db = open('/home/dramage/bikeshare-web/data/stations.json','r')
    except:
        syslog.syslog(syslog.LOG_ERR, "could not open stations.json")

    data = json.load(db)
    return json.dumps(data, ensure_ascii=True)
# Verb:     GET
# Route:    /REST/1.0/stations/all/<float:lat>/<float:lon>/<float:rad>
# Response: [ {<int:station_id>,<float:lat>,<float:lon>,<string:address>}, ... ]
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
# Form data: <int:station_id>
# Response:  {<int:bike_id>}
@app.route('/REST/1.0/bikes/checkout', methods=['POST'])
def checkout_bike():
    db = open('data/checkout.json','r')
    data = json.load(db)
    target_station = request.form['station_id']
    if target_station == str(data['station_id']):
        bikes = data['bikes']
        return json.dumps(bikes[0], ensure_ascii=True)
    return '{}', 403

# Checkin bike
# ---------
# Verb:      POST
# Route:     /REST/1.0/bikes/checkin
# Form data: <int:bike_id>,<int:station_id>
# Response:  {<float:price>,<float:discount>}
@app.route('/REST/1.0/bikes/checkin', methods=['POST'])
def checkin_bike():
    db = open('data/checkin.json','r')
    data = json.load(db)
    target_station = request.form['station_id']
    target_bike = request.form['bike_id']
    if target_station == str(data['station_id']):
        if data['num_docks'] > 0:
            price = float(data['price']) - (float(data['price']) * data['discount'])
            retn = { 'price': price, 'discount': data['discount'] }
            return json.dumps(retn, ensure_ascii=True)
    return '{}', 403

# Get/send recent bike positional data
# ---------
# Helper function which calls either the get or send version of this function,
# depending on which HTTP verb is used.
@app.route('/REST/1.0/bikes/pos/<int:bike_id>', methods=['GET','POST'])
def bike_pos(bike_id):
    if request.method == 'GET':
        return get_bike_position(bike_id)
    else:
        return send_bike_position(bike_id)
# Verb:     GET
# Route:    /REST/1.0/bikes/pos/<int:bike_id>
# Response: [ {<float:lat>,<float:lon>,<int:time>}, ... ]
def get_bike_position(bike_id):
    s = 'data/bikepos_' + str(bike_id) + '.json'
    try:
        db = open(s,'r')
    except IOError:
        return '{}', 404
    data = json.load(db)
    return json.dumps(data, ensure_ascii=True)
# Verb:      POST
# Route:     /REST/1.0/bikes/pos/<int:bike_id>
# Form data: <float:lat>,<float:lon>
# Response:  {}
def send_bike_position(bike_id):
    lat = request.form['lat']
    lon = request.form['lon']
    s = 'data/bikepos_' + str(bike_id) + '.json'
    try:
        db = open(s,'r')
    except IOError:
        return '{}', 404
    return '{}'


@app.route('/REST/1.0/riders/location', methods=['GET'])
def send_rider_data():
    riderData = []
    riderId = 0
    for route in routes:
        riderData.append({'rider_id' : riderId, 'location' : routes[riderId]['route'][routes[riderId]['routeIndex']]})
        routes[riderId]['routeIndex'] = (routes[riderId]['routeIndex'] + 1) % len(routes[riderId]['route'])
        riderId += 1
    print riderData
    return jsonify({'rider_locations' : riderData})


# Helper function. Extracts and returns only the set of key/value pairs that
# we want from a given dict.
def subdict(d, keys):
    d2 = dict()
    for k, v in d.iteritems():
        if k in keys:
            d2[k] = v
    return d2

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
        app.run(host='0.0.0.0', port=8089, debug=True)

