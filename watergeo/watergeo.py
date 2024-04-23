"""Main module."""
import ipyleaflet
from ipyleaflet import basemaps
import ipywidgets as widgets
import ee
import geopandas as gpd
import json
import requests
import os
import tempfile
from ipyleaflet import WidgetControl



class Map(ipyleaflet.Map):
    """This is the map class that inherits from ipyleaflet.Map.

    Args:
        ipyleaflet (Map): The ipyleaflet.Map class.
    """

    def __init__(self, center=[20, 0], zoom=2, **kwargs):
        """Initialize the map.

        Args:
            center (list, optional): Set the center of the map. Defaults to [20, 0].
            zoom (int, optional): Set the zoom level of the map. Defaults to 2.
        """

        if "scroll_wheel_zoom" not in kwargs:
            kwargs["scroll_wheel_zoom"] = True

        if "add_layer_control" not in kwargs:
            layer_control_flag = True
        else:
            layer_control_flag = kwargs["add_layer_control"]
        kwargs.pop("add_layer_control", None)

        super().__init__(center=center, zoom=zoom, **kwargs)
        if layer_control_flag:
            self.add_layers_control()
        
        self.basemap_gui_control = None

    def add_tile_layer(self, url, name, **kwargs):
        layer = ipyleaflet.TileLayer(url=url, name=name, **kwargs)
        self.add(layer)

    def add_basemap(self, name):
        """
        Adds a basemap to the current map.

        Args:
            name (str or object): The name of the basemap as a string, or an object representing the basemap.

        Raises:
            TypeError: If the name is neither a string nor an object representing a basemap.

        Returns:
            None
        """

        if isinstance(name, str):
            url = eval(f"basemaps.{name}").build_url()
            self.add_tile_layer(url, name)
        else:
            self.add(name)

    def add_layers_control(self, position="topright"):
        """Adds a layers control to the map.

        Args:
            position (str, optional): The position of the layers control. Defaults to "topright".
        """
        self.add_control(ipyleaflet.LayersControl(position=position))

    def add_geojson(self, data, name="geojson", **kwargs):
        """Adds a GeoJSON layer to the map.

        Args:
            data (str | dict): The GeoJSON data as a string or a dictionary.
            name (str, optional): The name of the layer. Defaults to "geojson".
        """
        import json

        if isinstance(data, str):
            with open(data) as f:
                data = json.load(f)

        if "style" not in kwargs:
            kwargs["style"] = {"color": "blue", "weight": 1, "fillOpacity": 0}

        if "hover_style" not in kwargs:
            kwargs["hover_style"] = {"fillColor": "#ff0000", "fillOpacity": 0.5}

        layer = ipyleaflet.GeoJSON(data=data, name=name, **kwargs)
        self.add(layer)

    def add_shp(self, data, name="shp", **kwargs):
        """
        Adds a shapefile to the current map.

        Args:
            data (str or dict): The path to the shapefile as a string, or a dictionary representing the shapefile.
            name (str, optional): The name of the layer. Defaults to "shp".
            **kwargs: Arbitrary keyword arguments.

        Raises:
            TypeError: If the data is neither a string nor a dictionary representing a shapefile.

        Returns:
            None
        """
        import shapefile
        import json

        if isinstance(data, str):
            with shapefile.Reader(data) as shp:
                data = shp.__geo_interface__

        self.add_geojson(data, name, **kwargs)

    def add_image(self, url, bounds, name="image", **kwargs):
        """Adds an image overlay to the map.

        Args:
            url (str): The URL of the image.
            bounds (list): The bounds of the image.
            name (str, optional): The name of the layer. Defaults to "image".
        """
        layer = ipyleaflet.ImageOverlay(url=url, bounds=bounds, name=name, **kwargs)
        self.add(layer)


    def add_raster(self, data, name="raster", zoom_to_layer=True, **kwargs):
        """Adds a raster layer to the map.

        Args:
        data (str): The path to the raster file or a URL.
        name (str, optional): The name of the layer. Defaults to "raster".
        """

        try:
            from localtileserver import TileClient, get_leaflet_tile_layer
        except ImportError:
            raise ImportError("Please install the localtileserver package.")

        if data.startswith('http://') or data.startswith('https://'):
            response = requests.get(data, stream=True)
            if response.status_code == 200:
                with tempfile.NamedTemporaryFile(delete=False) as fp:
                    for chunk in response.iter_content(1024):
                        fp.write(chunk)
                    data = fp.name
            else:
                raise ValueError(f"Failed to download {data}")

        client = TileClient(data)
        layer = get_leaflet_tile_layer(client, name=name, **kwargs)
        self.add(layer)

        if zoom_to_layer:
            self.center = client.center()
            self.zoom = client.default_zoom

        if data.startswith('http://') or data.startswith('https://'):
            os.unlink(data)

    def add_zoom_slider(
        self, description="Zoom level", min=0, max=24, value=10, position="topright"
    ):
        """Adds a zoom slider to the map.

        Args:
            position (str, optional): The position of the zoom slider. Defaults to "topright".
        """
        zoom_slider = widgets.IntSlider(
            description=description, min=min, max=max, value=value
        )

        control = ipyleaflet.WidgetControl(widget=zoom_slider, position=position)
        self.add(control)
        widgets.jslink((zoom_slider, "value"), (self, "zoom"))

    def add_widget(self, widget, position="topright"):
        """Adds a widget to the map.

        Args:
            widget (object): The widget to be added.
            position (str, optional): The position of the widget. Defaults to "topright".
        """
        control = ipyleaflet.WidgetControl(widget=widget, position=position)
        self.add(control)

    
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
                self.add_geojson(data, name, **kwargs)
            elif data.lower().endswith(('.shp')):
                # Read shapefile using GeoPandas and convert to GeoJSON
                gdf = gpd.read_file(data)
                self.add_geojson(gdf.__geo_interface__, name, **kwargs)
            else:
                raise TypeError("Unsupported vector data format.")
        elif isinstance(data, gpd.GeoDataFrame):
            self.add_geojson(data.__geo_interface__, name, **kwargs)
        elif isinstance(data, dict):
            self.add_geojson(data, name, **kwargs)
        else:
            raise TypeError("Unsupported vector data format.")
    
    def add_opacity_slider(
        self, layer_index=-1, description="Opacity", position="topright"
    ):
        """Adds an opacity slider to the map.

        Args:
            layer (object): The layer to which the opacity slider is added.
            description (str, optional): The description of the opacity slider. Defaults to "Opacity".
            position (str, optional): The position of the opacity slider. Defaults to "topright".
        """
        layer = self.layers[layer_index]
        opacity_slider = widgets.FloatSlider(
            description=description,
            min=0,
            max=1,
            value=layer.opacity,
            style={"description_width": "initial"},
        )

        def update_opacity(change):
            layer.opacity = change["new"]

        opacity_slider.observe(update_opacity, "value")

        control = ipyleaflet.WidgetControl(widget=opacity_slider, position=position)
        self.add(control)

    def add_basemap_gui(self, basemaps=None, position="topright"):
        """
        Adds a basemap GUI to the map. The GUI includes a dropdown list for selecting the basemap and a toggle button for showing and hiding the dropdown.
    
        The dropdown list includes options for different basemaps, such as "OpenStreetMap", "OpenTopoMap", "Esri.WorldImagery", and "Esri.NatGeoWorldMap". When a different option is selected in the dropdown, the basemap of the map is updated accordingly.
    
        The toggle button, represented by a 'times' icon when the dropdown is visible and a 'plus' icon when the dropdown is hidden, allows the user to show and hide the dropdown list. When the button is clicked, the visibility of the dropdown list is toggled.
    
        Args:
            basemaps (list, optional): A list of basemaps to include in the dropdown. If not provided, a default list of basemaps is used.
            position (str, optional): The position of the basemap GUI on the map. Defaults to "topright".
        """
        if self.basemap_gui_control is not None:  # Check if the basemap GUI is already displayed
            return  # If it is, do nothing and return
        basemap_selector = widgets.Dropdown(
            options=[
                "OpenStreetMap",
                "OpenTopoMap",
                "Esri.WorldImagery",
                "Esri.NatGeoWorldMap",
                "USGS Hydrography",
            ],
            description="Basemap",
        )
    
        toggle_button = widgets.Button(
            description="",
            button_style="primary",
            tooltip="Toggle dropdown",
            icon="times",
        )
        toggle_button.layout.width = "35px"
    
        def toggle_dropdown(b):
            if basemap_selector.layout.display == "none":
                basemap_selector.layout.display = ""
                toggle_button.icon = "times"
            else:
                basemap_selector.layout.display = "none"
                toggle_button.icon = "plus"
        toggle_button.on_click(toggle_dropdown)
    
        def update_basemap(change):
            self.add_basemap(change["new"])
        basemap_selector.observe(update_basemap, "value")

        
        # Create a box to hold the dropdown and the button
        box = widgets.HBox([basemap_selector, toggle_button])
    
        self.basemap_gui_control = WidgetControl(widget=box, position=position)
        self.add_control(self.basemap_gui_control)

        
    def add_toolbar(self, position="topright"):
        """Adds a toolbar to the map.

        Args:
            position (str, optional): The position of the toolbar. Defaults to "topright".
        """

        padding = "0px 0px 0px 5px"  # upper, right, bottom, left

        toolbar_button = widgets.ToggleButton(
            value=False,
            tooltip="Toolbar",
            icon="wrench",
            layout=widgets.Layout(width="28px", height="28px", padding=padding),
        )

        close_button = widgets.ToggleButton(
            value=False,
            tooltip="Close the tool",
            icon="times",
            button_style="primary",
            layout=widgets.Layout(height="28px", width="28px", padding=padding),
        )

        toolbar = widgets.VBox([toolbar_button])

        def close_click(change):
            if change["new"]:
                toolbar_button.close()
                close_button.close()
                toolbar.close()

        close_button.observe(close_click, "value")

        rows = 2
        cols = 2
        grid = widgets.GridspecLayout(
            rows, cols, grid_gap="0px", layout=widgets.Layout(width="65px")
        )

        icons = ["folder-open", "map", "info", "question"]

        for i in range(rows):
            for j in range(cols):
                grid[i, j] = widgets.Button(
                    description="",
                    button_style="primary",
                    icon=icons[i * rows + j],
                    layout=widgets.Layout(width="28px", padding="0px"),
                )

        def toolbar_click(change):
            if change["new"]:
                toolbar.children = [widgets.HBox([close_button, toolbar_button]), grid]
            else:
                toolbar.children = [toolbar_button]

        # Add a new button to the toolbar for the basemap GUI

        basemap_gui_button = widgets.Button(
            description="",
            button_style="primary",
            tooltip='Toggle',  # Set tooltip to a shorter string
            icon="globe",  # Use a different icon for the basemap GUI button
            layout=widgets.Layout(width="28px", padding="0px"),
        )

        basemap_gui_button.description = "off"
        grid[0, 0] = basemap_gui_button  # Replace this with the desired position

        toolbar_button.observe(toolbar_click, "value")
        toolbar_ctrl = WidgetControl(widget=toolbar, position="topright")
        self.add(toolbar_ctrl)        


        output = widgets.Output()
        output_control = WidgetControl(widget=output, position="bottomright")
        self.add(output_control)

        def toolbar_callback(change):
            with output:
                output.clear_output()
                if change.icon == "folder-open":
                    print(f"You can open a file")
                elif change.icon == "map":
                    print(f"You can add a layer")
                elif change.icon == "globe":
                    if basemap_gui_button.description == "off" and self.basemap_gui_control is None:  # Check if the basemap GUI is not displayed and not already added
                        self.add_basemap_gui()  # Call the add_basemap_gui function
                        basemap_gui_button.description = "on"  # Update the state of the button
                        print(f"Basemap GUI added")
                    else:  # If the basemap GUI is displayed
                        self.remove(self.basemap_gui_control)  # Remove the basemap GUI
                        self.basemap_gui_control = None  # Reset the basemap GUI control
                        basemap_gui_button.description = "off"  # Update the state of the button
                        print(f"Basemap GUI removed")
                
                else:
                    with output:
                        output.clear_output()
                    print(f"Icon: {change.icon}")

        for tool in grid.children:
            tool.on_click(toolbar_callback)

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
        layer = ipyleaflet.TileLayer(
            url=tiles_url,
            attribution='Google Earth Engine',
            name=name,
            opacity=opacity,
            visible=shown
        )
    
        # Add the layer to the map
        self.add_layer(layer)

    
    def add_split_map(self, left_layer, right_layer, left_vis_params={}, right_vis_params={}, left_layer_name='Left Layer', right_layer_name='Right Layer'):
        """
        Adds a split map with two layers and centers the map on the bounds of the layers.

        Args:
        left_layer (object): The Earth Engine object to display on the left side.
        right_layer (object): The Earth Engine object to display on the right side.
        left_vis_params (dict, optional): Visualization parameters for the left layer. Defaults to {}.
        right_vis_params (dict, optional): Visualization parameters for the right layer. Defaults to {}.
        left_layer_name (str, optional): The name of the left layer. Defaults to 'Left Layer'.
        right_layer_name (str, optional): The name of the right layer. Defaults to 'Right Layer'.
        """
        try:
            import ee  # Import ee here
            ee.Initialize()  # Initialize Earth Engine
            left_layer.getInfo()  # Check if the left layer object is valid
            right_layer.getInfo()  # Check if the right layer object is valid
        except Exception as e:
            print("Error adding Earth Engine layer:", e)
            return

        if isinstance(left_layer, ee.ImageCollection):
            left_layer = left_layer.mosaic()

        if isinstance(right_layer, ee.ImageCollection):
            right_layer = right_layer.mosaic()

        # Generate URLs for fetching the tiles from Earth Engine
        left_map_id_dict = ee.Image(left_layer).getMapId(left_vis_params)
        right_map_id_dict = ee.Image(right_layer).getMapId(right_vis_params)

        # Create new tile layers
        left_tiles_url = left_map_id_dict['tile_fetcher'].url_format
        right_tiles_url = right_map_id_dict['tile_fetcher'].url_format

        left_tile_layer = ipyleaflet.TileLayer(
            url=left_tiles_url,
            attribution='Google Earth Engine',
            name='Left Layer',
            opacity=1.0,
            visible=True
        )

        right_tile_layer = ipyleaflet.TileLayer(
            url=right_tiles_url,
            attribution='Google Earth Engine',
            name='Right Layer',
            opacity=1.0,
            visible=True
        )

        # Add the layers to the map
        self.add_layer(left_tile_layer)
        self.add_layer(right_tile_layer)

        # Get the bounds of the left and right layers
        left_bounds = ee.Image(left_layer).geometry().bounds().getInfo()['coordinates']
        right_bounds = ee.Image(right_layer).geometry().bounds().getInfo()['coordinates']
        
        # Calculate the center of the bounds
        left_center = [(left_bounds[0][0][0] + left_bounds[0][2][0]) / 2, (left_bounds[0][0][1] + left_bounds[0][2][1]) / 2]
        right_center = [(right_bounds[0][0][0] + right_bounds[0][2][0]) / 2, (right_bounds[0][0][1] + right_bounds[0][2][1]) / 2]
        
        # Calculate the average center between the two layers
        center = [(left_center[0] + right_center[0]) / 2, (left_center[1] + right_center[1]) / 2]
        
        # Center the map on the bounds
        self.center = center

        # Create a split control and add it to the map
        split_control = ipyleaflet.SplitMapControl(left_layer=left_tile_layer, right_layer=right_tile_layer)
        self.add_control(split_control)    