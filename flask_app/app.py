from decouple import config
from flask import Flask, render_template, request, jsonify
from flask_cors import CORS, cross_origin
from flask_migrate import Migrate
from .models import db, Quake
from flask_marshmallow import Marshmallow
import pandas as pd
import folium
import requests


def create_app():
    """Create and configure an instance of the Flask application"""
    app = Flask(__name__)
    cors = CORS(app)
    ma = Marshmallow(app)
    app.config['CORS_HEADERS'] = 'Content-Type'
    app.config['DEBUG'] = True
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SQLALCHEMY_DATABASE_URI'] = config('DATABASE_URI')
    class QuakeSchema(ma.Schema):
        class Meta:
            fields = ('id','longitude','latitude','depth','magnitude', 'place', 'time', 'felt')

    quake_schema = QuakeSchema()
    quakes_schema = QuakeSchema(many=True)
    db.init_app(app)
    #migrate = Migrate(app, db)

    @app.route('/grabquakes', methods=['POST', 'GET'])
    def grab_quakes():

        # This works best if it stays in this file, but consider moving to functions?
        def usgs_parser():
            '''
            Expects the database to be passed in, as well as a link to geojson data.
            If none is provided, it will default to the USGS' monthly geojson data
            for earthquakes of magnitude 4.5 and above.

            Database tables need to have:
            id (str),
            latitude (float),
            longitude (float),
            magnitude (float),
            place (str),
            time (int),
            felt (int, optional)
            '''
            # Uses the month-long geojson of 4.5 mag earthquakes and above
            usgs_data = requests.get('https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_day.geojson')

            for entry in usgs_data.json()['features']:
                # checks if entry already exists, then updates
                if db.session.query(Quake.id).filter_by(id=entry['id']).scalar() is not None:
                    updated_entry = Quake.query.filter_by(id=entry['id']).first()
                    updated_entry.longitude = entry['geometry']['coordinates'][0]
                    updated_entry.latitude = entry['geometry']['coordinates'][1]
                    updated_entry.depth = entry['geometry']['coordinates'][2]
                    updated_entry.magnitude = entry['properties']['mag']
                    updated_entry.place = entry['properties']['place']
                    updated_entry.time = entry['properties']['time']
                    updated_entry.felt = entry['properties']['felt']
                    db.session.commit()

                else:
                    try:
                        # Otherwise creates a new entry
                        quake_entry = Quake(id=entry['id'],
                        longitude=entry['geometry']['coordinates'][0],
                        latitude=entry['geometry']['coordinates'][1],
                        depths=entry['geometry']['coordinates'][2],
                        magnitude=entry['properties']['mag'],
                        place=entry['properties']['place'],
                        time=entry['properties']['time'])
                        db.session.add(quake_entry)

                    except Exception as e:
                        # prints message with the entry id if something goes wrong
                        print(f"Oh no {e} on {entry['id']}!")

        usgs_parser()
        db.session.commit()

        return render_template('grabquakes.html', title='Home', quakes=Quake.query.all())


    @app.route('/')
    def root():
        return render_template('base.html', title='Epicentral')

    @app.route('/map', methods=['POST', 'GET'])
    def map():

        # Defines Folium map based on geojson data
        usgs_month_data = 'https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/2.5_month.geojson'
        m = folium.Map(
            location=[-59.1759, -11.6016],
            tiles='Stamen Terrain',
            zoom_start=2  # Limited levels of zoom for free Mapbox tiles.
            )

        folium.GeoJson(
            usgs_month_data,
            name='geojson'
            ).add_to(m)
        m.save('templates/map.html')
        return render_template('map.html', title='Map data got!')

    @app.route('/getquakes', methods=['POST', 'GET'])
    @cross_origin()
    def getquakes():
        quakes = db.session.query(Quake).all()
        # json = jsonify(quakes_schema.dump(quakes))
        geojson = {
            "type": "FeatureCollection",
            "features": [
                        {
                            "type": "Feature",
                            "geometry" : {
                                "type": "Point",
                                "coordinates": [ii["longitude"], ii["latitude"], ii["depth"]]
                                        },
                            "properties" : ii,
                            "title" : f"M {ii['magnitude']} - {ii['place']}"
                    } for ii in quakes_schema.dump(quakes)]
                        }
        return geojson

    # Remember to delete for production phase
    @app.route('/reset')
    def reset():
        db.drop_all()
        db.create_all()
        return render_template('base.html', title='Reset database!')

    return app
