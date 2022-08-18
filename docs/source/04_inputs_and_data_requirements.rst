.. _inputs_and_data_requirements:

===============================
4. Inputs and Data Requirements
===============================

CanFlood models are only as useful as the datasets they are built with. Below is a summary of the main datasets the user must collect and compile prior to building a CanFlood model.

.. _Section4.1:

********************
4.1. Asset Inventory
********************

The asset inventory (‘finv’) is a comprehensive list of the objects or assets whose exposure will be evaluated by the CanFlood model routines. The asset inventory is a spatial dataset that requires the following fields when employed in Risk (L1) models:

  • *fX_scale*: value to scale the vulnerability function by (e.g., floor area);
  • *fX_elv*: elevation to anchor the vulnerability function (e.g., first floor height + DTM);
  • *geometry*: geospatial data used to locate the asset for sampling;
  • *FieldName Index (cid)*: unique asset identifying integer used to link datasets.

For Impacts (L2) and Risk (L2) models, the following additional fields are required:

  • *fX_tag*: value telling the model which vulnerability function to assign to this asset;
  • *fX_cap*: value to cap vulnerability prediction by (e.g., improvement value).

Additional fields are allowed but ignored by CanFlood. The ‘X’ placeholder shown above is called the ‘nestID’ and is used to group the four key attributes that parametrize a ‘nested function’ required by the Impacts (L2) model (:ref:`Section5.2.2 <Section5.2.2>`). The ‘Build’ toolset provides a ‘Inventory Constructor’ tool that can populate an inventory template as a convenience; however, completing this template for a study area generally requires extensive data analysis outside the CanFlood plugin.

.. _Section4.2:

******************
4.2. Hazard Events
******************

CanFlood requires a set of ‘hazard events’ to calculate flood exposure and risk. For a risk calculation, each event should have:

  • **Event probability**: probability of the event occurring. This can be input as Annual Exceedance Probabilities (AEP) or Annual Recurrence Intervals (ARI). Often these are developed using statistical analysis of past flood events. As this information is not contained in the raster data file itself, best practice is to include it in the layer name.

  • **Event raster**: location and WSL of the flood event. CanFlood’s ‘Hazard Sampler’ tool (:ref:`Section5.1.3 <Section5.1.3>`) expects this as a raster data file, but CanFlood’s Model routines only require the tabular exposure data (‘expos’). Values must be relative to the project datum (WSL) and are typically developed using hydraulic modelling software.

  • **Companion failure events (optional)**: contains information about the probability and resulting exposure of a flood protection system failure during the hazard event. Each hazard event can be assigned multiple failure events (see :ref:`Section1.4 <Section1.4>`) by specifying the same event probability for each in the ‘evals’ dataset (see :ref:`Section5.1.4 <Section5.1.4>`).

      o Failure raster: location and WSL of the companion failure event.

      o Failure polygon: Conditional exposure probability polygon layer with features indicating the extent and probability of element failures during the event. The ‘Dike Fragility Mapper’ tool (:ref:`Section5.1.5 <Section5.1.5>`) provides a set of algorithms for preparing these polygons from typical dike fragility information and event rasters. These failure polygons are needed by the ‘Conditional P’ tool to generate the resolved exposure probabilities (‘exlikes’) dataset required by the Risk (L1) and Risk (L2) modules.

.. _Section4.3:

*******************************
4.3. Vulnerability Function Set
*******************************

For the Impacts (L2) model, CanFlood requires an impact function library with a function for each asset tag in the inventory. The datafile is a .xls spreadsheet, where each tab corresponds to a separate impact function. Each tab contains:

  • metadata about the function (not used by CanFlood); and
  • a 1D function translating exposure to impact.

An example is provided below with a description. During the Impacts (L2) model, each asset interpolates its vulnerability function at the exposure value (from the ‘expos’ data set) to estimate the impact value. Typically, the exposure variables are depth and the impact variables are damages, but the user can customize the model by populating the ‘expos’ data set with alternative exposure variables and developing vulnerability functions with alternative outputs (e.g. persons displaced = f(percent inundated)).

*Table 4-1: CanFlood impact function format requirements and description.*

   
.. csv-table:: 
   :file: /tables/41_impactFunctionFormat.csv
   :widths: auto
   :header-rows: 1

.. _Section4.4:

********************************
4.4. Digital Terrain Model (DTM)
********************************

A project DTM is only required for those models with relative asset heights (elv).

.. _Section4.5:

*********************
4.5. Dike Information
*********************

To use the ‘Dike Fragility Mapper’ module (:ref:`Section5.4.1 <Section5.4.1>`) to generate the ‘failure polygon’ set, the following information on the study area’s diking system is required:

    • **Dike alignment**: This line layer contains the following information on the study dikes:
        o face of the dike: indicated by the direction of the feature, this tells CanFlood which side should of the feature to sample the WSL from

        o the horizontal location of the dike crest (i.e. the position of features)

        o how each dike should be segmented in the analysis (where each feature represents a segment)

        o the dike identifier (for combining multiple segments onto a single plot)

        o any freeboard buffers that should be applied (e.g., to simulate sand-bagging)

        o which fragility curve should be used to calculate the failure probability of that segment.

    • **Dike fragility function library**: This special type of impact function (Section4.3_) relates the WSL relative to the segment crest elevation (i.e., freeboard) against the probability of that segment failing (and realizing the provided failure WSL). Developing these relations often requires data on mechanical (e.g., foundation, core) and emergency repair properties (e.g., accessibility to maintenance vehicles) and sophisticated geotechnical analysis and expertise. While dike performance is generally sensitive to more types of loading than freeboard, CanFlood only supports single-variable fragility calculations.

    • **Dike segment influence areas**: These polygons provide the geometry of the area where assets would be impacted by a failure of a segment. Generally, this is similar to the extents of the failure raster (e.g., results of a hydraulic model breach run).

    • **Digital Terrain Model (DTM) of dike crest**: This is generally the same dataset as what’s described in Section4.4_; however, dike evaluation is particular sensitive to small changes in elevation and DTMs often have errors or artifacts around dike crests if not constructed for flood modelling. Therefore, users should emphasize DTM quality around dike crests when performing a fragility analysis.