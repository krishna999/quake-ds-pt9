from decouple import config
import folium
from flask import Flask, render_template, request

from mapping.home_to_coords import city_to_coords

def create_app():
    """Create and configure an instance of the Flask application"""
    app = Flask(__name__)
    # DB.init_app(app)

    @app.route('/')
    def root():
        return render_template('base.html', title='Epicentral')

    @app.route('/map', methods=['POST', 'GET'])
    def map():
        start_coords = city_to_coords('Los Angeles, CA')
        folium_map = folium.Map(location=start_coords, zoom_start=10)
        return folium_map._repr_html_()

    return app