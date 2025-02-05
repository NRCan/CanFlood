import pytest
import configparser
from misc.webConnections import WebConnect
from PyQt5.QtCore import QSettings

@pytest.fixture(scope="function")
def web_connect(tmpdir):
    """Fixture to provide an instance of WebConnect with a temporary QGIS3.ini file."""
    qini_fp = tmpdir.join("QGIS3.ini")
    qini_fp.write("[connections]\n")

    web_connect = WebConnect(qini_fp=str(qini_fp))

    settings = QSettings(str(qini_fp), QSettings.IniFormat)
    settings.clear()  
    settings.sync()

    yield web_connect

@pytest.fixture(scope="function")
def create_config(tmpdir, config_content):
    """Fixture to create a temporary config file with the specified content."""
    config = configparser.ConfigParser()
    config.read_dict(config_content)
    config_file_path = tmpdir.join("test_config.ini")
    
    with open(config_file_path, 'w') as configfile:
        config.write(configfile)
    
    return str(config_file_path)

@pytest.mark.parametrize(
    "config_content, expected_key",
    [
        ({"AutomaticallyExtractedBuildings": {
            "group": "connections-wms\\NRCan_AutomaticallyExtractedBuildings",
            "url": "https://maps.geogratis.gc.ca/wms/automatic_extraction_building_footprint_en?request=getcapabilities&service=wms&layers=automatic_extraction_building_footprint_en&version=1.3.0&legend_format=image/png&feature_info_type=text/html"
        }}, "connections/ows/items/wms/connections/items/AutomaticallyExtractedBuildings/url"),

        ({"GAR15": {
            "group": "connections-wcs\\UNISDR_GAR15_GlobalRiskAssessment",
            "url": "http://preview.grid.unep.ch/geoserver/wcs"
        }}, "connections/ows/items/wcs/connections/items/GAR15/url"),

        ({"NPRI": {
            "group": "connections-arcgisfeatureserver\\ECCC_NationalPollutantReleaseInventory_NPRI",
            "url": "http://preview.grid.unep.ch/geoserver/wcs?bbox=-180,-89,180,84&styles=&version=1.0.0&coverage=GAR2015:flood_hazard_1000_yrp&width=640&height=309&crs=EPSG:4326"
        }}, "connections/arcgisfeatureserver/items/NPRI/url")
    ]
)
def test_read_connections(web_connect, create_config, config_content, expected_key):
    """Test the read_connections function and check expected QGIS3.ini structure."""
    config_path = create_config  

    web_connect.read_connections(config_path)

    settings = QSettings(web_connect.qini_fp, QSettings.IniFormat)
    settings.sync() 

    assert expected_key in settings.allKeys(), f"Expected key '{expected_key}' was not found in the updated QGIS3.ini file"
