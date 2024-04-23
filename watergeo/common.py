"""The common module contains common functions and classes used by the other modules.
"""
import ee
import os
import requests
import zipfile


def hello_world():
    """Prints "Hello World!" to the console.
    """
    print("Hello World!")

def filter_polygons(ftr):
    """Converts GeometryCollection to Polygon/MultiPolygon

    Args:
        ftr (object): ee.Feature

    Returns:
        object: ee.Feature
    """
    # ee_initialize()
    geometries = ftr.geometry().geometries()
    geometries = geometries.map(
        lambda geo: ee.Feature(ee.Geometry(geo)).set("geoType", ee.Geometry(geo).type())
    )

    polygons = (
        ee.FeatureCollection(geometries)
        .filter(ee.Filter.eq("geoType", "Polygon"))
        .geometry()
    )
    return ee.Feature(polygons).copyProperties(ftr)

def ee_export_vector(
    ee_object,
    filename,
    selectors=None,
    verbose=True,
    keep_zip=False,
    timeout=300,
    proxies=None,
):
    """Exports Earth Engine FeatureCollection to other formats, including shp, csv, json, kml, and kmz.

    Args:
        ee_object (object): ee.FeatureCollection to export.
        filename (str): Output file name.
        selectors (list, optional): A list of attributes to export. Defaults to None.
        verbose (bool, optional): Whether to print out descriptive text.
        keep_zip (bool, optional): Whether to keep the downloaded shapefile as a zip file.
        timeout (int, optional): Timeout in seconds. Defaults to 300 seconds.
        proxies (dict, optional): A dictionary of proxies to use. Defaults to None.
    """

    if not isinstance(ee_object, ee.FeatureCollection):
        raise ValueError("ee_object must be an ee.FeatureCollection")

    allowed_formats = ["csv", "geojson", "json", "kml", "kmz", "shp"]
    # allowed_formats = ['csv', 'kml', 'kmz']
    filename = os.path.abspath(filename)
    basename = os.path.basename(filename)
    name = os.path.splitext(basename)[0]
    filetype = os.path.splitext(basename)[1][1:].lower()

    if filetype == "shp":
        filename = filename.replace(".shp", ".zip")

    if not (filetype.lower() in allowed_formats):
        raise ValueError(
            "The file type must be one of the following: {}".format(
                ", ".join(allowed_formats)
            )
        )

    if selectors is None:
        selectors = ee_object.first().propertyNames().getInfo()
        if filetype == "csv":
            # remove .geo coordinate field
            ee_object = ee_object.select([".*"], None, False)

    if filetype == "geojson":
        selectors = [".geo"] + selectors

    elif not isinstance(selectors, list):
        raise ValueError(
            "selectors must be a list, such as ['attribute1', 'attribute2']"
        )
    else:
        allowed_attributes = ee_object.first().propertyNames().getInfo()
        for attribute in selectors:
            if not (attribute in allowed_attributes):
                raise ValueError(
                    "Attributes must be one chosen from: {} ".format(
                        ", ".join(allowed_attributes)
                    )
                )

    try:
        if verbose:
            print("Generating URL ...")
        url = ee_object.getDownloadURL(
            filetype=filetype, selectors=selectors, filename=name
        )
        if verbose:
            print(f"Downloading data from {url}\nPlease wait ...")
        r = None
        r = requests.get(url, stream=True, timeout=timeout, proxies=proxies)

        if r.status_code != 200:
            print("An error occurred while downloading. \n Retrying ...")
            try:
                new_ee_object = ee_object.map(filter_polygons)
                print("Generating URL ...")
                url = new_ee_object.getDownloadURL(
                    filetype=filetype, selectors=selectors, filename=name
                )
                print(f"Downloading data from {url}\nPlease wait ...")
                r = requests.get(url, stream=True, timeout=timeout, proxies=proxies)
            except Exception as e:
                print(e)
                raise ValueError

        with open(filename, "wb") as fd:
            for chunk in r.iter_content(chunk_size=1024):
                fd.write(chunk)
    except Exception as e:
        print("An error occurred while downloading.")
        if r is not None:
            print(r.json()["error"]["message"])
        raise ValueError(e)

    try:
        if filetype == "shp":
            with zipfile.ZipFile(filename) as z:
                z.extractall(os.path.dirname(filename))
            if not keep_zip:
                os.remove(filename)
            filename = filename.replace(".zip", ".shp")
        if verbose:
            print(f"Data downloaded to {filename}")
    except Exception as e:
        raise ValueError(e)
    

def zonal_stats(
    in_value_raster,
    in_zone_vector,
    out_file_path=None,
    stat_type="MEAN",
    scale=None,
    crs=None,
    tile_scale=1.0,
    return_fc=False,
    verbose=True,
    timeout=300,
    proxies=None,
    **kwargs,
):
    """Summarizes the values of a raster within the zones of another dataset and exports the results as a csv, shp, json, kml, or kmz.

    Args:
        in_value_raster (object): An ee.Image or ee.ImageCollection that contains the values on which to calculate a statistic.
        in_zone_vector (object): An ee.FeatureCollection that defines the zones.
        out_file_path (str): Output file path that will contain the summary of the values in each zone. The file type can be: csv, shp, json, kml, kmz
        stat_type (str, optional): Statistical type to be calculated. Defaults to 'MEAN'. For 'HIST', you can provide three parameters: max_buckets, min_bucket_width, and max_raw. For 'FIXED_HIST', you must provide three parameters: hist_min, hist_max, and hist_steps.
        scale (float, optional): A nominal scale in meters of the projection to work in. Defaults to None.
        crs (str, optional): The projection to work in. If unspecified, the projection of the image's first band is used. If specified in addition to scale, rescaled to the specified scale. Defaults to None.
        tile_scale (float, optional): A scaling factor used to reduce aggregation tile size; using a larger tileScale (e.g. 2 or 4) may enable computations that run out of memory with the default. Defaults to 1.0.
        verbose (bool, optional): Whether to print descriptive text when the programming is running. Default to True.
        return_fc (bool, optional): Whether to return the results as an ee.FeatureCollection. Defaults to False.
        timeout (int, optional): Timeout in seconds. Default to 300.
        proxies (dict, optional): A dictionary of proxy servers to use for the request. Default to None.
    """

    if isinstance(in_value_raster, ee.ImageCollection):
        in_value_raster = in_value_raster.toBands()

    if not isinstance(in_value_raster, ee.Image):
        print("The input raster must be an ee.Image.")
        return

    if not isinstance(in_zone_vector, ee.FeatureCollection):
        print("The input zone data must be an ee.FeatureCollection.")
        return

    if out_file_path is None:
        out_file_path = os.path.join(os.getcwd(), "zonal_stats.csv")

    if "statistics_type" in kwargs:
        stat_type = kwargs.pop("statistics_type")

    allowed_formats = ["csv", "geojson", "kml", "kmz", "shp"]
    filename = os.path.abspath(out_file_path)
    basename = os.path.basename(filename)
    # name = os.path.splitext(basename)[0]
    filetype = os.path.splitext(basename)[1][1:].lower()

    if not (filetype in allowed_formats):
        print(
            "The file type must be one of the following: {}".format(
                ", ".join(allowed_formats)
            )
        )
        return

    # Parameters for histogram
    # The maximum number of buckets to use when building a histogram; will be rounded up to a power of 2.
    max_buckets = None
    # The minimum histogram bucket width, or null to allow any power of 2.
    min_bucket_width = None
    # The number of values to accumulate before building the initial histogram.
    max_raw = None
    hist_min = 1.0  # The lower (inclusive) bound of the first bucket.
    hist_max = 100.0  # The upper (exclusive) bound of the last bucket.
    hist_steps = 10  # The number of buckets to use.

    if "max_buckets" in kwargs.keys():
        max_buckets = kwargs["max_buckets"]
    if "min_bucket_width" in kwargs.keys():
        min_bucket_width = kwargs["min_bucket"]
    if "max_raw" in kwargs.keys():
        max_raw = kwargs["max_raw"]

    if isinstance(stat_type, str):
        if (
            stat_type.upper() == "FIXED_HIST"
            and ("hist_min" in kwargs.keys())
            and ("hist_max" in kwargs.keys())
            and ("hist_steps" in kwargs.keys())
        ):
            hist_min = kwargs["hist_min"]
            hist_max = kwargs["hist_max"]
            hist_steps = kwargs["hist_steps"]
        elif stat_type.upper() == "FIXED_HIST":
            print(
                "To use fixedHistogram, please provide these three parameters: hist_min, hist_max, and hist_steps."
            )
            return

    allowed_statistics = {
        "COUNT": ee.Reducer.count(),
        "MEAN": ee.Reducer.mean(),
        "MEAN_UNWEIGHTED": ee.Reducer.mean().unweighted(),
        "MAXIMUM": ee.Reducer.max(),
        "MEDIAN": ee.Reducer.median(),
        "MINIMUM": ee.Reducer.min(),
        "MODE": ee.Reducer.mode(),
        "STD": ee.Reducer.stdDev(),
        "MIN_MAX": ee.Reducer.minMax(),
        "SUM": ee.Reducer.sum(),
        "VARIANCE": ee.Reducer.variance(),
        "HIST": ee.Reducer.histogram(
            maxBuckets=max_buckets, minBucketWidth=min_bucket_width, maxRaw=max_raw
        ),
        "FIXED_HIST": ee.Reducer.fixedHistogram(hist_min, hist_max, hist_steps),
        "COMBINED_COUNT_MEAN": ee.Reducer.count().combine(
            ee.Reducer.mean(), sharedInputs=True
        ),
        "COMBINED_COUNT_MEAN_UNWEIGHTED": ee.Reducer.count().combine(
            ee.Reducer.mean().unweighted(), sharedInputs=True
        ),
    }

    if isinstance(stat_type, str):
        if not (stat_type.upper() in allowed_statistics.keys()):
            print(
                "The statistics type must be one of the following: {}".format(
                    ", ".join(list(allowed_statistics.keys()))
                )
            )
            return
        reducer = allowed_statistics[stat_type.upper()]
    elif isinstance(stat_type, ee.Reducer):
        reducer = stat_type
    else:
        raise ValueError("statistics_type must be either a string or ee.Reducer.")

    if scale is None:
        scale = in_value_raster.projection().nominalScale().multiply(10)

    try:
        if verbose:
            print("Computing statistics ...")
        result = in_value_raster.reduceRegions(
            collection=in_zone_vector,
            reducer=reducer,
            scale=scale,
            crs=crs,
            tileScale=tile_scale,
        )
        if return_fc:
            return result
        else:
            ee_export_vector(result, filename, timeout=timeout, proxies=proxies)
    except Exception as e:
        raise Exception(e)


zonal_statistics = zonal_stats