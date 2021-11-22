







=========
Footnotes
=========

.. [1] All SOFDA inputs must be built and configured manually.

.. [2] The ‘capped’ values with null and rounding treatment.

.. [3] Can be built from an .xls file by exporting to csv then creating a csv layer in QGIS from the lat/long values.

.. [4] A corresponding simple $/m2 curve is created by the DamageCurves Converter.

.. [5] Depending on your settings, this may have been set automatically when you loaded the datafiles. 
   All tutorials   use CRS ‘EPSG:3005’ unless stated otherwise. See the following link for an explanation of projections in QGIS.

   https://docs.qgis.org/3.10/en/docs/user_manual/working_with_projections/working_with_projections.html

.. [6] Depending on your QGIS settings, you may be requested to select a transformation if the CRS was not 
   set correctly beforehand.

.. [7] Any field with unique integer values can be used as the FieldName Index (except built-in feature identifiers).

.. [8] If the hazard layers are not shown in the dialog, hit ‘Refresh’.

.. [9] does not have to match the directory from the previous step.

.. [10] CanFlood will attempt to automatically identify the Inventory Vector Layer; however, this tutorial does 
   not make use of this layer so the selection here can be ignored.

.. [11] If the filepath fails to populate automatically, try changing re-setting the ‘finv’ and ‘parameter’ 
   drop-downs. Alternatively, enter the filepath manually.

.. [12] Some ‘Results’ tools work better when the model output data files are in the same file tree as the 
   Control File.

.. [13] Try running the tool again, but this time selecting ‘Max’. If you look closely at the boxplots, you should 
   see a slight difference in the resolved probabilities. This suggests this model is not very sensitive to the relational assumption of these overlapping failure polygons.

.. [14] Alternatively, the ‘Compare’ tool can be used to generate a comparison plot between the two tutorials.

.. [15] Advanced users could avoid re-running the ‘Impacts (L2)’ model by manipulating the Control File to point 
   to the ‘dmgs’ results from the previous run as these will not change between the two formulations.

.. [16] The control file specified on the ‘Setup’ tab will be used for common plot styles (e.g.,

.. [17] The influence of the mitigation functions on the depths are not reflected in this output.

.. [18] Alternatively, the ‘tut2d_noMiti’ from Tutorial 2d can be used.

.. [19] If you get a B/C ratio of 1.19, make sure the $1000 maintenance costs are entered for every year of the 
   life-cycle.

.. [20] Available in the CanFlood styles package described in Section 5.4.4 (Plugins > CanFlood > Add Styles).

.. [21] Be sure to load the stylized ‘.qlr’ layers in place of the raw layers.

.. [22] This is important for inundation percent analysis which deals with small fractions.

.. [23] Risk (L1) inundation percentage runs can not use asset elevations; therefore, this input variable is 
   redundant. When as_inun=True CanFlood model routines expect an ‘elv’ column with all zeros.

.. [24] See Rudari and Silvestro (2015) for details on the GAR15 flood hazard model.

.. [25] Depending on your profile settings, the project’s CRS may be automatically set by the first loaded layer.

.. [26] New installations of Qgis should automatically path to the same profile directory (Settings > User Profiles > 
   Open Active Profile Folder), therefore carrying forward your previous connection info.

.. [27] Ctrl+Shift+F will zoom to the project extents.

.. [28] Depending on your internet connection, this process can be slow. It’s recommended to set ‘Cache’=’Prefer
   cache’ to limit additional data transfers, and to turn the layers off or disable rendering once loaded into the project.

.. [29] You can safely select any transformation or close the dialog. These transformations are only for display, 
   we’ll deal with transforming the data onto our CRS below.

.. [30] In some cases, QGIS may fail to recognize the CRS assigned to these new rasters, indicated by a “?” shown to 
   the right of the layer in the layers panel. In these cases, you will need to define the projection by going to the layer’s ‘Properties’ and under ‘Source’ set the coordinate system to match that of the project (EPSG: 3978).

.. [31] Load these styles onto your profile using the Plugins>CanFlood>Add Styles tool described in Section 5.4.4.

.. _appendix_a:

===========================
Appendix A: Web Connections
===========================

+---------------------------------------------+--------------------------------------------------------+---------------------+----------------+-+
| Acronym                                     | Description                                            | Service             | Reference      | |
+=============================================+========================================================+=====================+================+=+
| UNISDR_GAR15_GlobalRiskAssessment           |                                                        |                                        |
+---------------------------------------------+--------------------------------------------------------+---------------------+----------------+-+
| GAR15                                       | UNISDR’s data layers from the global risk assessment   | WCS                 | see below      | |
|                                             | conducted for the Global Assessment Report on          |                     |                | |
|                                             | Disaster Risk Reduction 2015 (GAR15) by the CIMA       |                     |                | |
|                                             | Research Foundation. This data is hosted by the        |                     |                | |
|                                             | Global Risk Data Platform and contains six global      |                     |                | |
|                                             | flood depth rasters (in cm; return periods = 25, 50,   |                     |                | |
|                                             | 100, 200, 500, 1000 years) having 1km resolution.      |                     |                | |
+---------------------------------------------+--------------------------------------------------------+---------------------+----------------+-+
| ECCC_NationalPollutantReleaseInventory_NPRI |                                                        |                                        |
+---------------------------------------------+--------------------------------------------------------+---------------------+----------------+-+
| NPRI                                        | Government of Canada’s service to collect information  | ArcGisFeatureServer | `homepage`_    | |
|                                             | on the release, disposal and transfer of more than 320 |                     |                | |
|                                             | substances. The web-service provides release reports   |                     |                | |
|                                             | from the most recent year. The layer ‘NPRI-Reporting   |                     |                | |
|                                             | Facilities’ shows the location of facilitates          |                     |                | |
|                                             | reporting any type of release.                         |                     |                | |
+---------------------------------------------+--------------------------------------------------------+---------------------+----------------+-+
| NRCan_NationalHumanSettlementLayer_NHSL     |                                                        |                                        |
+---------------------------------------------+--------------------------------------------------------+---------------------+----------------+-+
| NHSL                                        | Collection of thematic datasets that describe the      | ArcGisFeatureServer | `MapServer`_   | |
|                                             | physical, social and economic characteristics of       |                     |                | |
|                                             | urban centres and rural/remote communities across      |                     |                | |
|                                             | Canada, and their vulnerability to natural hazards     |                     |                | |
|                                             | of concern                                             |                     |                | |
+---------------------------------------------+--------------------------------------------------------+---------------------+----------------+-+
| NRCan_AutomaticallyExtractedBuildings       |                                                        |                                        |
+---------------------------------------------+--------------------------------------------------------+---------------------+----------------+-+
|                                             | Topographical feature class that delineates            | WMS                 | `Open Canada`_ | |
|                                             | polygonal building footprints automatically            |                     |                | |
|                                             | extracted from airborne Lidar data, high-resolution    |                     |                | |
|                                             | optical imagery or other sources.                      |                     |                | |
+---------------------------------------------+--------------------------------------------------------+---------------------+----------------+-+

.. _homepage: https://www.canada.ca/en/services/environment/pollution-waste-management/national-pollutant-release-inventory.html

.. _MapServer: https://maps-cartes.services.geo.ca/server_serveur/rest/services/NRCan/nhsl_en/MapServer

.. _Open Canada: https://open.canada.ca/data/en/dataset/7a5cda52-c7df-427f-9ced-26f19a8a64d6

GAR15
=====

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

.. _appendix_b:

=============================
Appendix B: SOFDA User Manual
=============================

https://github.com/IBIGroupCanWest/CanFlood/tree/master/manual/sofda/

.. |buildimage| image:: /_static/build_image.jpg
   :align: middle
   :width: 22

.. |runimage| image:: /_static/run_image.jpg
   :align: middle
   :width: 22

.. |visualimage| image:: /_static/visual_image.jpg
   :align: middle
   :width: 22

.. |diamondimage| image:: /_static/red_diamond_image.jpg
   :align: middle
   :width: 22

.. |lineimage| image:: /_static/horizontal_line_image.jpg
   :align: middle
   :width: 22

.. |dotimage| image:: /_static/green_dot_image.jpg
   :align: middle
   :width: 22

.. |ss| raw:: html

    <strike>

.. |se| raw:: html

    </strike>
