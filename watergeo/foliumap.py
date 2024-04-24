import folium
from ipyleaflet import basemaps
import ee
from folium import plugins
import geopandas as gpd
import json


class Map(folium.Map):

    def __init__(self, center=[20, 0], zoom=2, **kwargs):
        super().__init__(location=center, zoom_start=zoom, **kwargs)

        if not ee.data._initialized:
            ee.Authenticate()
            ee.Initialize()

    def add_raster(self, data, name="raster", zoom_to_layer=True, **kwargs):

        """Adds a raster layer to the map.

        Args:
            data (str): The path to the raster file.
            name (str, optional): The name of the layer. Defaults to "raster".
        """

        try:
            from localtileserver import TileClient, get_folium_tile_layer
        except ImportError:
            raise ImportError("Please install the localtileserver package.")

        client = TileClient(data)
        layer = get_folium_tile_layer(client, name=name, **kwargs)
        layer.add_to(self)


    def add_tile_layer(self, url, name, attribution="Custom Tile", **kwargs):
        """
        Adds a tile layer to the current map.

        Args:
            url (str): The URL of the tile layer.
            name (str): The name of the layer.
            attribution (str, optional): The attribution text to be displayed for the layer. Defaults to "Custom Tile".
            **kwargs: Arbitrary keyword arguments for additional layer options.

        Returns:
            None
        """
        layer = folium.TileLayer(tiles=url, name=name, attr=attribution, **kwargs)
        layer.add_to(self)

    def add_basemap(self, name, overlay=True):
        """
        Adds a basemap to the current map.

        Args:
            name (str or object): The name of the basemap as a string, or an object representing the basemap.
            overlay (bool, optional): Whether the basemap is an overlay. Defaults to True.

        Raises:
            TypeError: If the name is neither a string nor an object representing a basemap.

        Returns:
            None
        """

        if isinstance(name, str):
            url = eval(f"basemaps.{name}").build_url()
            self.add_tile_layer(url, name, overlay=overlay)
        else:
            name.add_to(self)

    def to_streamlit(self, width=700, height=500):
        """
        Converts the map to a streamlit component.

        Args:
            width (int, optional): The width of the map. Defaults to 700.
            height (int, optional): The height of the map. Defaults to 500.

        Returns:
            object: The streamlit component representing the map.
        """

        from streamlit_folium import folium_static

        return folium_static(self, width=width, height=height)

    def add_layer_control(self):
        """
        Adds a layer control to the map.

        Returns:
            None
        """

        folium.LayerControl().add_to(self)

    def add_ee_layer(self, ee_object, vis_params, name):
        """
        Adds a Earth Engine layer to the current map.

        Args:
            ee_object (object): The Earth Engine object to be displayed.
            vis_params (dict): Visualization parameters as a dictionary.
            name (str): The name of the layer.

        Returns:
            None
        """
        ee.Initialize()
        try:
            # Convert the Earth Engine layer to a TileLayer that can be added to a folium map.
            map_id_dict = ee.Image(ee_object).getMapId(vis_params)
            folium.raster_layers.TileLayer(
                tiles=map_id_dict['tile_fetcher'].url_format,
                attr='Map Data &copy; <a href="https://earthengine.google.com/">Google Earth Engine</a>',
                name=name,
                overlay=True,
                control=True
            ).add_to(self)
        except Exception as e:
            print(f"Could not display {name}: {e}")

    def add_geojson(self, data, name="geojson", **kwargs):
        """Adds a GeoJSON layer to the map.

        Args:
            data (str | dict): The GeoJSON data as a string or a dictionary.
            name (str, optional): The name of the layer. Defaults to "geojson".
        """
        if isinstance(data, str):
            with open(data) as f:
                data = json.load(f)

        folium.GeoJson(data, name=name, **kwargs).add_to(self)

    def add_shp(self, data, name="shp", **kwargs):
        """
        Adds a shapefile to the current map.

        Args:
            data (str or dict): The path to the shapefile as a string, or a dictionary representing the shapefile.
            name (str, optional): The name of the layer. Defaults to "shp".
            **kwargs: Arbitrary keyword arguments.
        """
        if isinstance(data, str):
            data = gpd.read_file(data).to_json()

        self.add_geojson(data, name, **kwargs)


    def add_vector(self, data, name="vector", **kwargs):
        """
        Adds a vector layer to the current map.

        Args:
            data (str, GeoDataFrame, dict): The vector data as a string (path to file), GeoDataFrame, or a dictionary.
            name (str, optional): The name of the layer. Defaults to "vector".
            **kwargs: Arbitrary keyword arguments.

        Raises:
            TypeError: If the data is not in a supported format.

        Returns:
            None
        """
        if isinstance(data, str):
            if data.lower().endswith(('.geojson', '.json')):
                # Load GeoJSON directly
                with open(data) as f:
                    data = json.load(f)
                folium.GeoJson(data, name=name, **kwargs).add_to(self)
            elif data.lower().endswith(('.shp')):
                # Read shapefile using GeoPandas and convert to GeoJSON
                gdf = gpd.read_file(data)
                folium.GeoJson(gdf.__geo_interface__, name=name, **kwargs).add_to(self)
            else:
                raise TypeError("Unsupported vector data format.")
        elif isinstance(data, gpd.GeoDataFrame):
            folium.GeoJson(data.__geo_interface__, name=name, **kwargs).add_to(self)
        elif isinstance(data, dict):
            folium.GeoJson(data, name=name, **kwargs).add_to(self)
        else:
            raise TypeError("Unsupported vector data format.")   
        
    
    
    
    def add_split_map(map_object, layer1, layer2, vis_params1, vis_params2):
        # Create a DualMap
        m = folium.plugins.DualMap()
    
        # Convert the layers to Earth Engine Images
        image1 = ee.Image(layer1)
        image2 = ee.Image(layer2)
    
        # Get the map ID dictionaries
        map_id_dict1 = image1.getMapId(vis_params1)
        map_id_dict2 = image2.getMapId(vis_params2)
    
        # Create the tile layers
        tile_layer1 = folium.TileLayer(
            tiles=map_id_dict1['tile_fetcher'].url_format,
            attr='Google Earth Engine',
            overlay=True,
            name='layer1',
        )
        tile_layer2 = folium.TileLayer(
            tiles=map_id_dict2['tile_fetcher'].url_format,
            attr='Google Earth Engine',
            overlay=True,
            name='layer2',
        )
    
        # Add the layers to the DualMap
        tile_layer1.add_to(m.m1)
        tile_layer2.add_to(m.m2)
    
        # Add the DualMap to the original map
        map_object.add_child(m)