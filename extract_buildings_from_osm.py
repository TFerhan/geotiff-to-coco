import osmnx as ox
import geopandas as gpd
import pandas as pd

def from_osm_to_gdf(osm_path, output_path):
    buildings = ox.features_from_xml(osm_path)
    tf = buildings.reset_index()
    df_buildings = tf[(tf["element"] == "way") & (tf["building"].notna())]
    builff = df_buildings[["building", "geometry"]].reset_index(drop=True)
    gdf_buildings = gpd.GeoDataFrame(builff, geometry="geometry", crs="EPSG:4326")
    builff.to_csv(output_path, index=False)
    return builff
