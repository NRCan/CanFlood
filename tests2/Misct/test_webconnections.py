import pytest
import configparser
from misc.webConnections import WebConnect

# Test cases for parameterization
test_cases = {
    "valid_wms_connection": {
        "config_content": {
            "AutomaticallyExtractedBuildings": {
                "group": "connections-wms\\NRCan_AutomaticallyExtractedBuildings",  # Matches the original format
                "url": "https://maps.geogratis.gc.ca/wms/automatic_extraction_building_footprint_en?request=getcapabilities&service=wms&layers=automatic_extraction_building_footprint_en&version=1.3.0&legend_format=image/png&feature_info_type=text/html"
            }
        },
        "expected_result": "AutomaticallyExtractedBuildings"
    },
    "valid_wcs_connection": {
        "config_content": {
            "GAR15": {
                "group": "connections-wcs\\UNISDR_GAR15_GlobalRiskAssessment",  # Matches the original format
                "url": "http://preview.grid.unep.ch/geoserver/wcs?bbox=-180,-89,180,84&styles=&version=1.0.0&coverage=GAR2015:flood_hazard_1000_yrp&width=640&height=309&crs=EPSG:4326"
            }
        },
        "expected_result": "GAR15"
    },
    "valid_arcgis_connection": {
        "config_content": {
            "NPRI": {
                "group": "connections-arcgisfeatureserver\\ECCC_NationalPollutantReleaseInventory_NPRI",  # Matches the original format
                "url": "https://maps-cartes.ec.gc.ca/arcgis/rest/services/STB_DGST/NPRI/MapServer"
            }
        },
        "expected_result": "NPRI"
    },
    "invalid_connection_type": {
        "config_content": {
            "invalid_connection": {
                "group": "connections-invalid",
                "url": "http://example.com/invalid"
            }
        },
        "expected_error": ValueError
    }
}

@pytest.fixture(scope="function")
def web_connect(tmpdir):
    """Fixture to provide an instance of WebConnect with mocked QGIS settings."""
    # Create a temporary QGIS settings file (qini_fp)
    qini_fp = tmpdir.join("QGIS3.ini")
    qini_fp.write("[qgis]\n")  

    web_connect = WebConnect(qini_fp=str(qini_fp))
    yield web_connect

@pytest.fixture(scope="function")
def config_file(tmpdir, request):
    """Fixture to create a temporary config file with the specified content."""
    config = configparser.ConfigParser()
    config.read_dict(test_cases[request.param]["config_content"])
    config_file_path = tmpdir.join("test_config.ini")
    with open(config_file_path, 'w') as configfile:
        config.write(configfile)
    yield config_file_path

@pytest.mark.parametrize(
    "config_file, expected_result, expected_error",
    [
        ("valid_wms_connection", "AutomaticallyExtractedBuildings", None),
        ("valid_wcs_connection", "GAR15", None),
        ("valid_arcgis_connection", "NPRI", None),
        ("invalid_connection_type", None, ValueError)
    ],
    indirect=["config_file"]
)
def test_read_connections(web_connect, config_file, expected_result, expected_error):
    """Test the read_connections function with different configurations."""
    print("CONFIG FILE:", config_file)
    if expected_error:
        print("EXPECTED ERROR:", expected_error)
        with pytest.raises(expected_error):
            web_connect.read_connections(config_file)
    else:
        print("EXPECTED RESULT:", expected_result)
        web_connect.read_connections(config_file)
        # Debugging: Print the contents of newCons_d
        print("Contents of newCons_d:", web_connect.newCons_d)
        # Check that the connection was added correctly
        assert expected_result in web_connect.newCons_d