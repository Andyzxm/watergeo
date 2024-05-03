"""Top-level package for watergeo."""

__author__ = """Xinming Zhang"""
__email__ = "andyzxm1101@gmail.com"
__version__ = "0.1.0"
import os
from .watergeo import *

def _in_colab_shell():
    """Tests if the code is being executed within Google Colab."""
    import sys

    if "google.colab" in sys.modules:
        return True
    else:
        return False
    
def _use_folium():
    """Whether to use the folium or ipyleaflet plotting backend."""
    if os.environ.get("USE_MKDOCS") is not None:
        return True
    else:
        return False
def view_pmtiles(
    url,
    style=None,
    name=None,
    tooltip=True,
    overlay=True,
    control=True,
    show=True,
    zoom_to_layer=True,
    map_args={},
    **kwargs,
):
    """
    Visualize PMTiles the map.

    Args:
        url (str): The URL of the PMTiles file.
        style (str, optional): The CSS style to apply to the layer. Defaults to None.
            See https://docs.mapbox.com/style-spec/reference/layers/ for more info.
        name (str, optional): The name of the layer. Defaults to None.
        tooltip (bool, optional): Whether to show a tooltip when hovering over the layer. Defaults to True.
        overlay (bool, optional): Whether the layer should be added as an overlay. Defaults to True.
        control (bool, optional): Whether to include the layer in the layer control. Defaults to True.
        show (bool, optional): Whether the layer should be shown initially. Defaults to True.
        zoom_to_layer (bool, optional): Whether to zoom to the layer extent. Defaults to True.
        **kwargs: Additional keyword arguments to pass to the PMTilesLayer constructor.

    Returns:
        folium.Map: A folium Map object.
    """

    from .foliumap import Map

    m = Map(**map_args)
    m.add_pmtiles(
        url, style, name, tooltip, overlay, control, show, zoom_to_layer, **kwargs
    )
    return m


if _use_folium():
    from .foliumap import *
else:
    try:
        from .watergeo import *
    except Exception as e:
        if _in_colab_shell():
            print(
                "Please restart Colab runtime after installation if you encounter any errors when importing leafmap."
            )
        else:
            print(
                "Please restart Jupyter kernel after installation if you encounter any errors when importing leafmap."
            )
        raise Exception(e)