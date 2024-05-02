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
        

    def add_time_slider(self, ee_image_collection, vis_params, name_prefix):
        """
        Adds a time slider to the map.

        Args:
            ee_image_collection (object): The Earth Engine ImageCollection to be displayed.
            vis_params (dict): Visualization parameters as a dictionary.
            name_prefix (str): The prefix of the name of the layers.

        Returns:
            None
        """
        try:
            # Convert the Earth Engine ImageCollection to a list of Images
            image_list = ee_image_collection.toList(ee_image_collection.size())

            # Get the number of images
            n = image_list.size().getInfo()

            for i in range(n):
                # Get the i-th image in the list
                image = ee.Image(image_list.get(i))

                # Get the date of the image
                date = image.date().format('YYYY-MM-dd').getInfo()

                # Convert the Earth Engine layer to a TileLayer that can be added to a folium map.
                map_id_dict = image.getMapId(vis_params)

                # Add the layer to the map
                folium.raster_layers.TileLayer(
                    tiles=map_id_dict['tile_fetcher'].url_format,
                    attr='Google Earth Engine',
                    name=f"{name_prefix} {date}",
                    overlay=True,
                    control=True
                ).add_to(self)
        except Exception as e:
            print(f"Could not display {name_prefix}: {e}")

    def split_map(self, layer1, layer2, vis_params1, vis_params2, outline_layer=None):
        """
        Creates a split map with the given layers and visualization parameters.

        Args:
            layer1 (object): The first Earth Engine layer to be displayed.
            layer2 (object): The second Earth Engine layer to be displayed.
            vis_params1 (dict): Visualization parameters for the first layer.
            vis_params2 (dict): Visualization parameters for the second layer.
            outline_layer (object, optional): An optional Earth Engine layer to be displayed on both sides of the split map.

        Returns:
            folium.plugins.DualMap: The split map.
        """
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

        # Create a DualMap
        m = folium.plugins.DualMap(location=[0, 0], zoom_start=2)

        # Add the layers to the map
        m.m1.add_child(tile_layer1)
        m.m2.add_child(tile_layer2)

        # If an outline layer is provided, add it to both sides of the split map
        if outline_layer is not None:
            # Convert the outline layer to an Earth Engine Image
            outline_image = ee.Image(outline_layer)

            # Get the map ID dictionary
            outline_map_id_dict = outline_image.getMapId()

            # Create the outline tile layer
            outline_tile_layer = folium.TileLayer(
                tiles=outline_map_id_dict['tile_fetcher'].url_format,
                attr='Google Earth Engine',
                overlay=True,
                name='outline',
            )

            # Add the outline layer to the map
            m.m1.add_child(outline_tile_layer)
            m.m2.add_child(outline_tile_layer)

        # Return the split map
        return m

    def add_choropleth(self, geo_data, data, columns, key_on, fill_color='YlGn', fill_opacity=0.7, line_opacity=0.2, legend_name='Legend'):
        """
        Add a choropleth layer to the map.

        Parameters:
        geo_data (str or dict): URL, file path, or data (json/dict) that represents the geojson geometries.
        data (DataFrame): Pandas dataframe containing the data.
        columns (list): The columns in the dataframe that contain the key and values.
        key_on (str): Variable in the `geo_data` file that contains the key.
        fill_color (str, optional): Area fill color. Defaults to 'YlGn'.
        fill_opacity (float, optional): Area fill opacity. Defaults to 0.7.
        line_opacity (float, optional): Line opacity. Defaults to 0.2.
        legend_name (str, optional): Legend title. Defaults to 'Legend'.
        """

        # Add the choropleth layer to the map
        folium.Choropleth(
            geo_data=geo_data,
            data=data,
            columns=columns,
            key_on=key_on,
            fill_color=fill_color,
            fill_opacity=fill_opacity,
            line_opacity=line_opacity,
            legend_name=legend_name
        ).add_to(self)

        return self