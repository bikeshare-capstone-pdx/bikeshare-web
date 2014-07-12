var pointFeature;
var map;
var stationLayer;
var featuresToStationIds = []
var features = []
//this is entirely temporary and will be obtained by ajax later
var routePoint = 0;
var bikeFeature;
var riderFeatures = {};

function init() {
    map = new OpenLayers.Map("mapdiv");
    //switch between local and remote tiles
    var tileLayer = new OpenLayers.Layer.OSM("Local Tiles", "http://bikeshare.cs.pdx.edu/osm/${z}/${x}/${y}.png", {numZoomLevels: 19, crossOriginKeyword: null});
    //var tileLayer = new OpenLayers.Layer.OSM();
    map.addLayer(tileLayer); 
    // allow testing of specific renderers via "?renderer=Canvas", etc
    var renderer = OpenLayers.Util.getParameters(window.location.href).renderer;
    renderer = (renderer) ? [renderer] : OpenLayers.Layer.Vector.prototype.renderers;
    var layer_style = OpenLayers.Util.extend({}, OpenLayers.Feature.Vector.style['default']);
    layer_style.fillOpacity = 0.2;
    layer_style.graphicOpacity = 1;
    var lonlat = new OpenLayers.LonLat(-122.680591,45.510016).transform(
        new OpenLayers.Projection("EPSG:4326"), // transform from WGS 1984
        new OpenLayers.Projection("EPSG:900913") // to Spherical Mercator
      );
    stationLayer = new OpenLayers.Layer.Vector("Simple Geometry", {
        styleMap: new OpenLayers.StyleMap({'default':{
            strokeColor: "${pointColor}",
            strokeOpacity: 1,
            strokeWidth: 3,
            fillColor: "${pointColor}",
            fillOpacity: 0.8,
            pointRadius: 5,
            pointerEvents: "visiblePainted",
            label : "${name}",
            fontColor: "${favColor}",
            fontSize: "12px",
            fontFamily: "Courier New, monospace",
            fontWeight: "bold",
            labelAlign: "${align}",
            labelXOffset: "${xOffset}",
            labelYOffset: "${yOffset}"
        }}),
        renderers: renderer
    });
    stationLayer.events.register("featuresadded", stationLayer, function() {
        stationLayer.redraw();
    });
    map.addLayer(stationLayer);
    var zoom = 14;
      map.setCenter(lonlat, zoom); 
      bikeLayer = new OpenLayers.Layer.Vector("bikeLayer", {
          style : {
              externalGraphic : "http://bikeshare.cs.pdx.edu/bikeshare_dramage/static/ic_launcher32.png",
              graphicWidth: 21,
              graphicHeight: 25
          }
    });
    map.addLayer(bikeLayer);
     var highlightCtrl = new OpenLayers.Control.SelectFeature(stationLayer, {
                hover: true,
                eventListeners: {
                    featurehighlighted: featureHighlighted,
                    featureunhighlighted: featureUnhighlighted 
        }
     });
    
    map.addControl(highlightCtrl);
    highlightCtrl.activate();
    map.setCenter(lonlat, zoom);
    createBikeshareStationFeatures();
    //createBikeFeatures();
    createRiderFeatures();
}

function createBikeFeatures() {
    var bikePoint = new OpenLayers.Geometry.Point(route[0][0],route[0][1]);
    bikePoint.transform(
        new OpenLayers.Projection("EPSG:4326"),
        new OpenLayers.Projection("EPSG:900913")
    );
    bikeFeature = new OpenLayers.Feature.Vector(bikePoint);
    bikeLayer.addFeatures([bikeFeature]);
}

function createRiderFeatures() {
    $.ajax({url :  "http://bikeshare.cs.pdx.edu/bikeshare_dramage//REST/1.0/riders/location",
        success : function(result) {
            createRiderPoints(result.rider_locations);
        }
    });
}



function createRiderPoints(rider_locations) {
    for (var i = 0; i < rider_locations.length; i ++ ) {
        console.log(rider_locations[i]);
        var bikePoint = new OpenLayers.Geometry.Point(rider_locations[i]['location'][0],rider_locations[i]['location'][1]);
        bikePoint.transform(
            new OpenLayers.Projection("EPSG:4326"),
            new OpenLayers.Projection("EPSG:900913")
        );
        riderFeatures[rider_locations[i]['rider_id']] = new OpenLayers.Feature.Vector(bikePoint);
        bikeLayer.addFeatures([riderFeatures[rider_locations[i]['rider_id']]]);
    }
    bikeLayer.redraw();
}
function getBikestationData() {
    for (var i = 0; i < featuresToStationIds.length; i ++) {
       $.ajax({ url : "http://bikeshare.cs.pdx.edu/bikeshare_dramage/REST/1.0/stations/info/" + featuresToStationIds[i],
            success : function(result) {
                stationData = JSON.parse(result);
                setStationColor(this.stationFeatureId,stationData);  
                return;          
            },
            stationFeatureId : i
       });
    }
    stationLayer.redraw();
}

function setStationColor(stationNum,stationData) {
    bikePercent = (stationData.num_bikes / stationData.num_docks) * 100;
    if (bikePercent >= 70) {
        features[stationNum].attributes.pointColor = 'blue';
    } else if (70 > bikePercent >= 40) {
        features[stationNum].attributes.pointColor = 'yellow';
    } else {
        features[stationNum].attributes.pointColor = 'red';
    }
}
function getRandomInt (min, max) {
  	return Math.floor(Math.random() * (max - min + 1)) + min;
}


function getRiderData() {
    $.ajax({url :  "http://bikeshare.cs.pdx.edu/bikeshare_dramage//REST/1.0/riders/location",
        success : function(result) {
            updateRiderPoints(result.rider_locations);
        }
    });
}

function updateRiderPoints(rider_locations) {
    for (feature in bikeLayer.features) {
        bikeLayer.removeFeatures([feature]);
    }
    for (var i = 0; i < rider_locations.length; i ++ ) {
        console.log(rider_locations[i]);
        var bikePoint = new OpenLayers.Geometry.Point(rider_locations[i]['location'][0],rider_locations[i]['location'][1]);
        bikePoint.transform(
            new OpenLayers.Projection("EPSG:4326"),
            new OpenLayers.Projection("EPSG:900913")
        );
        bikeLayer.removeFeatures([riderFeatures[rider_locations[i]['rider_id']]]);
        riderFeatures[rider_locations[i]['rider_id']].geometry = bikePoint;
        bikeLayer.addFeatures([riderFeatures[rider_locations[i]['rider_id']]]);
    }
    bikeLayer.redraw();
}


function featureHighlighted(feature) {
    var popupIndex = getPopupIndex(feature.feature.attributes.popup);
    map.popups[popupIndex].show();
}

function featureUnhighlighted(feature) {
    var popupIndex = getPopupIndex(feature.feature.attributes.popup);
    map.popups[popupIndex].hide(); 
}
function createBikeshareStationFeatures() {
    $.ajax({url : "http://bikeshare.cs.pdx.edu/bikeshare_dramage/REST/1.0/stations/all",
    success: function(result) {
        bikeStationList = JSON.parse(result);
        for (var i = 0; i < bikeStationList.length; i ++) {
            $.ajax({url : "http://bikeshare.cs.pdx.edu/bikeshare_dramage/REST/1.0/stations/info/" + bikeStationList[i].station_id,
            success: function(result) {
                        stationData = JSON.parse(result);
                        createStationFeature(this.lon,this.lat,this.stationId,stationData.num_bikes,stationData.num_docks,this.stationIndex);
                    },
                    stationId : bikeStationList[i].station_id,
                    lat : bikeStationList[i].lat,
                    lon : bikeStationList[i].lon,
                    stationIndex : i 
            });
        }
     }
   });
}

function createStationFeature(lon,lat,stationId,bikes,docks,index) {
   var bikePercent = (bikes/docks) * 100;
   var pointColor;
   if (bikePercent > 70) {
        pointColor = 'blue';
   } else if (70 > bikePercent >= 40) {
        pointColor = 'yellow';
   } else {
        pointColor = 'red';
   }
   var stationPoint = new OpenLayers.Geometry.Point(lon,lat);
   stationPoint.transform(
        new OpenLayers.Projection("EPSG:4326"),
        new OpenLayers.Projection("EPSG:900913")
   );
   pointFeature = new OpenLayers.Feature.Vector(stationPoint);
   pointFeature.attributes = {
       name : "BikeShare Station " + stationId,
       favColor : 'black',
       align : 'cm',
       xOffset : 10,
       yOffset : 10,
       pointColor : pointColor,
       stationId : stationId,
       index: index,
       lat : lat,
       lon : lon
   };
   pointFeature.attributes.popup = new OpenLayers.Popup.FramedCloud("Popup" + stationId,
        stationPoint.getBounds().getCenterLonLat(), null,
        'Station ' + stationId + '</br>Bikes ' + bikes + '</br>Docks ' + docks,
        null,
        false
   );
   stationLayer.addFeatures([pointFeature]);
   map.addPopup(pointFeature.attributes.popup);
   //map.popups[index] = pointFeature.attributes.popup;
   for (var j = 0; j < map.popups.length; j ++) {
        map.popups[j].hide();
   }
}

function updateBikestationData() {
    for (var i = 0; i < map.popups.length; i ++) {
        map.popups[i].destroy();
    }
    for (var i = 0; i < stationLayer.features.length; i ++) {
        $.ajax({url : "http://bikeshare.cs.pdx.edu/bikeshare_dramage/REST/1.0/stations/info/" + stationLayer.features[i].attributes.stationId,
             success: function(result) {
                    stationData = JSON.parse(result);
                    updateStationFeature(this.lon,this.lat,this.stationId,stationData.num_bikes,stationData.num_docks,this.stationId,this.index);
              },
              index : stationLayer.features[i].attributes.index,
              stationId : stationLayer.features[i].attributes.stationId,
              lat : stationLayer.features[i].attributes.lat,
              lon : stationLayer.features[i].attributes.lon,
              stationId : stationLayer.features[i].attributes.stationId
       });
    }
}

function updateStationFeature(lon,lat,stationId,bikes,docks,stationId,index) {
    var bikePercent = (bikes/docks) * 100;
    var pointColor;
    if (bikePercent > 70) {
         pointColor = 'blue';
    } else if (70 > bikePercent >= 40) {
         pointColor = 'yellow';
    } else {
         pointColor = 'red';
    }
    stationLayer.features[index].attributes.pointColor = pointColor;
    stationLayer.redraw();
   var stationPoint = new OpenLayers.Geometry.Point(lon,lat);
   stationPoint.transform(
        new OpenLayers.Projection("EPSG:4326"),
        new OpenLayers.Projection("EPSG:900913")
   );

   stationLayer.features[index].attributes.popup = new OpenLayers.Popup.FramedCloud("Popup" + stationId,
        stationPoint.getBounds().getCenterLonLat(), null,
        'Station ' + stationId + '</br>Bikes ' + bikes + '</br>Docks ' + docks,
        null,
        false
   );
   map.addPopup(stationLayer.features[index].attributes.popup);
   for (var i = 0; i < map.popups.length; i ++) {
       map.popups[i].hide();
   }
}

function getPopupIndex(popup) {
    popupIdx = -1;
    for (var i = 0; i < map.popups.length; i ++) {
        if (popup.id == map.popups[i].id) {
            popupIdx = i;
        }
    }
    return popupIdx;
}
setInterval(function(){updateBikestationData()},15000);
//setInterval(function(){moveBike()},1000);
setInterval(function(){getRiderData()},1000);
