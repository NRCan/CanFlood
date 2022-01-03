.. _appendix_a:

============================
Appendix A: Web Connections
============================

+---------------+--------------------------------------------------------+----------------------+------------------+
| Acronym       | Description                                            | Service              | Reference        |
+===============+========================================================+======================+==================+
| UNISDR_GAR15_GlobalRiskAssessment                                                                                |
+---------------+--------------------------------------------------------+----------------------+------------------+
| GAR15         | UNISDR’s data layers from the global risk assessment   | WCS                  | see below        | 
|               | conducted for the Global Assessment Report on          |                      |                  |
|               | Disaster Risk Reduction 2015 (GAR15) by the CIMA       |                      |                  |
|               | Research Foundation. This data is hosted by the        |                      |                  |
|               | Global Risk Data Platform and contains six global      |                      |                  | 
|               | flood depth rasters (in cm; return periods = 25, 50,   |                      |                  |
|               | 100, 200, 500, 1000 years) having 1km resolution.      |                      |                  |
+---------------+--------------------------------------------------------+----------------------+------------------+
| ECCC_NationalPollutantReleaseInventory_NPRI                                                                      |
+---------------+--------------------------------------------------------+----------------------+------------------+
| NPRI          | Government of Canada’s service to collect information  | ArcGisFeatureServer  | `homepage`_      | 
|               | on the release, disposal and transfer of more than 320 |                      |                  |
|               | substances. The web-service provides release reports   |                      |                  |
|               | from the most recent year. The layer ‘NPRI-Reporting   |                      |                  |
|               | Facilities’ shows the location of facilitates          |                      |                  | 
|               | reporting any type of release.                         |                      |                  |
+---------------+--------------------------------------------------------+----------------------+------------------+
| NRCan_NationalHumanSettlementLayer_NHSL                                                                          |
+---------------+--------------------------------------------------------+----------------------+------------------+
| NHSL          | Collection of thematic datasets that describe the      | ArcGisFeatureServer  | `MapServer`_     | 
|               | physical, social and economic characteristics of       |                      |                  |
|               | urban centres and rural/remote communities across      |                      |                  |
|               | Canada, and their vulnerability to natural hazards     |                      |                  |
|               | of concern                                             |                      |                  | 
+---------------+--------------------------------------------------------+----------------------+------------------+
| NRCan_AutomaticallyExtractedBuildings                                                                            |
+---------------+--------------------------------------------------------+----------------------+------------------+
|               | Topographical feature class that delineates            | WMS                  | `Open Canada`_   | 
|               | polygonal building footprints automatically            |                      |                  |
|               | extracted from airborne Lidar data, high-resolution    |                      |                  |
|               | optical imagery or other sources.                      |                      |                  |
+---------------+--------------------------------------------------------+----------------------+------------------+

.. _homepage: https://www.canada.ca/en/services/environment/pollution-waste-management/national-pollutant-release-inventory.html

.. _MapServer: https://maps-cartes.services.geo.ca/server_serveur/rest/services/NRCan/nhsl_en/MapServer

.. _Open Canada: https://open.canada.ca/data/en/dataset/7a5cda52-c7df-427f-9ced-26f19a8a64d6

GAR15
==========

**Server**

Global Risk Data Platform 

(https://preview.grid.unep.ch/index.php?preview=home&lang=eng)

Data and Model

From preventionweb (https://risk.preventionweb.net/capraviewer/):

  *The GAR Atlas global flood hazard assessment uses a probabilistic approach for modelling riverine flood major river basins around the globe. This has been possible after compiling a global database of stream-flow data, merging different sources and gathering more than 8000 stations over the globe in order to calculate the range of possible discharges from very low to the maximum possible scales at different locations along the rivers. The calculated discharges were introduced in the river sections to model water levels downstream. This procedure allowed for the determination of stochastic event-sets of riverine floods from which hazard maps for several return periods (25, 50, 100, 200, 500, 1000 years) were obtained. The hazard maps are developed at 1kmx1km resolution and have been validated against satellite flood footprints from different sources (DFO archive, UNOSAT flood portal) performing well especially for big events For smaller events (lower return periods), the GAR Atlas flood hazard maps tend to overestimate with respect to similar maps produced locally (hazard maps where available for some countries and were used as benchmark). The main issue being that, due to the resolution, the GAR Atlas flood hazard maps do not take into account flood defenses that are normally present to preserve the value exposed to floods.*

Additional summary is provided in:

  UNISDR. 2015. “Global Assessment Report on Disaster Risk Reduction 2015 - Annex

    1 - Global Risk Assessment.” Geneva: United Nations. https://www.preventionweb.net/english/hyogo/gar/2015/en/gar-pdf/Annex1-GAR_Global_Risk_Assessment_Data_methodology_and_usage.pdf.

Additional detail is provided in:

  Rudari, Roberto, and Francesco Silvestro. 2015. “IMPROVEMENT OF THE GLOBAL FLOOD MODEL FOR THE GAR 2015.” UNISDR.

    `https://www.preventionweb.net/english/hyogo/gar/2015/.. <https://www.preventionweb.net/english/hyogo/gar/2015/en/bgdocs/risk-section/CIMA%20Foundation,%20Improvement%20of%20the%20Global%20Flood%20Model%20for%20the%20GAR15.pdf>`__.
