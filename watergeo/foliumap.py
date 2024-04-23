import folium
import ee

class Map(folium.Map):

    def __init__(self, center=[20, 0], zoom=2, **kwargs):
        super().__init__(location=center, zoom_start=zoom, **kwargs)
        
    def add_raster(self, data, name="raster", **kwargs):
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
    
    def add_ee_layer(self, ee_object, vis_params={}, name="Layer untitled", shown=True, opacity=1.0):
        """
        Adds Earth Engine data layers to the map.
    
        Args:
            ee_object (object): The Earth Engine object to add to the map.
            vis_params (dict, optional): Visualization parameters. Defaults to {}.
            name (str, optional): The name of the layer. Defaults to "Layer untitled".
            shown (bool, optional): Whether to show the layer initially. Defaults to True.
            opacity (float, optional): The opacity of the layer (between 0 and 1). Defaults to 1.0.
        """
        try:
            import ee  # Import ee here
            ee.Initialize()  # Initialize Earth Engine
            ee_object.getInfo()  # Check if the object is valid
        except Exception as e:
            print("Error adding Earth Engine layer:", e)
            return
    
        if isinstance(ee_object, ee.ImageCollection):
            ee_object = ee_object.mosaic()
    
        # Generate a URL for fetching the tiles from Earth Engine
        map_id_dict = ee.Image(ee_object).getMapId(vis_params)
    
        # Create a new tile layer
        tiles_url = map_id_dict['tile_fetcher'].url_format
        folium.TileLayer(
            tiles=tiles_url,
            attr='Google Earth Engine',
            name=name,
            overlay=True,
            control=True
        ).add_to(self)