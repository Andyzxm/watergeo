import folium
from typing import Optional
import ee

class Map(folium.Map):
    """The Map class inherits folium.Map. By default, the Map will add OpenStreetMap as the basemap.

    Returns:
        object: folium map object.
    """

    def __init__(self, **kwargs):
        # Default map center location and zoom level
        latlon = [20, 0]
        zoom = 2

        # Interchangeable parameters between ipyleaflet and folium
        if "center" in kwargs:
            kwargs["location"] = kwargs["center"]
            kwargs.pop("center")
        if "location" in kwargs:
            latlon = kwargs["location"]
        else:
            kwargs["location"] = latlon

        if "zoom" in kwargs:
            kwargs["zoom_start"] = kwargs["zoom"]
            kwargs.pop("zoom")
        if "zoom_start" in kwargs:
            zoom = kwargs["zoom_start"]
        else:
            kwargs["zoom_start"] = zoom
        if "max_zoom" not in kwargs:
            kwargs["max_zoom"] = 24

        if "scale_control" not in kwargs:
            kwargs["scale_control"] = True

        if kwargs["scale_control"]:
            kwargs["control_scale"] = True
            kwargs.pop("scale_control")

        # if "control_scale" not in kwargs:
        #     kwargs["control_scale"] = True

        if "draw_export" not in kwargs:
            kwargs["draw_export"] = False

        if "height" in kwargs and isinstance(kwargs["height"], str):
            kwargs["height"] = float(kwargs["height"].replace("px", ""))

        if (
            "width" in kwargs
            and isinstance(kwargs["width"], str)
            and ("%" not in kwargs["width"])
        ):
            kwargs["width"] = float(kwargs["width"].replace("px", ""))

        height = None
        width = None

        if "height" in kwargs:
            height = kwargs.pop("height")
        else:
            height = 600

        if "width" in kwargs:
            width = kwargs.pop("width")
        else:
            width = "100%"

        super().__init__(**kwargs)
        self.baseclass = "folium"


    def add_layer(self, layer):
        """Adds a layer to the map.

        Args:
            layer (TileLayer): A TileLayer instance.
        """
        layer.add_to(self)
    
    def add_basemap(self, basemap):
        if basemap == "OpenStreetMap":
            folium.TileLayer('openstreetmap').add_to(self)
        elif basemap == "Stamen Terrain":
            folium.TileLayer('stamenterrain').add_to(self)
        elif basemap == "Stamen Toner":
            folium.TileLayer('stamentoner').add_to(self)

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

    def to_streamlit(
        self,
        width: Optional[int] = None,
        height: Optional[int] = 600,
        scrolling: Optional[bool] = False,
        add_layer_control: Optional[bool] = True,
        bidirectional: Optional[bool] = False,
        **kwargs,
    ):
        """Renders `folium.Figure` or `folium.Map` in a Streamlit app. This method is a static Streamlit Component, meaning, no information is passed back from Leaflet on browser interaction.

        Args:
            width (int, optional): Width of the map. Defaults to None.
            height (int, optional): Height of the map. Defaults to 600.
            scrolling (bool, optional): Whether to allow the map to scroll. Defaults to False.
            add_layer_control (bool, optional): Whether to add the layer control. Defaults to True.
            bidirectional (bool, optional): Whether to add bidirectional functionality to the map. The streamlit-folium package is required to use the bidirectional functionality. Defaults to False.

        Raises:
            ImportError: If streamlit is not installed.

        Returns:
            streamlit.components: components.html object.
        """

        try:
            import streamlit.components.v1 as components

            if add_layer_control:
                self.add_layer_control()

            if bidirectional:
                from streamlit_folium import st_folium

                output = st_folium(self, width=width, height=height)
                return output
            else:
                # if responsive:
                #     make_map_responsive = """
                #     <style>
                #     [title~="st.iframe"] { width: 100%}
                #     </style>
                #     """
                #     st.markdown(make_map_responsive, unsafe_allow_html=True)
                return components.html(
                    self.to_html(), width=width, height=height, scrolling=scrolling
                )

        except Exception as e:
            raise Exception(e)