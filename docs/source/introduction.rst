.. _introduction:

============================
1. Introduction
============================

CanFlood is an object-based, transparent, open-source flood risk calculation toolbox built for Canada. CanFlood facilitates flood risk calculations with three ‘toolsets’:

  1) Building a model  |buildimage|                      

  2) Running a model   |runimage|                       
  
  3) Visualizing and analyzing results   |visualimage|

Each of these has a suite of tools to assist the flood risk modeller in a wide range of tasks common in developing flood risk assessments in Canada.

CanFlood flood risk models are object-based, where consequences from flood exposure are calculated for each asset (e.g., a house) using a one-dimensional user-supplied vulnerability function (i.e., depth-damage function) before summing the consequences on each asset and integrating a range of events to obtain the total flood risk in an area. To support the diversity of flood risk assessment needs and data availability across Canada, CanFlood supports three modelling frameworks of increasing complexity, data requirements, and effort (Section1.1_). Each of these frameworks was designed to be flexible and agnostic, allowing modellers to implement a single software tool and data structure while maintaining flood risk models that reflect the heterogeneity of Canadian assets and values. Recognizing the significance of flood protection infrastructure on flood risk in many Canadian communities, CanFlood models can incorporate failure potential into risk calculations. To make use of Canada’s growing collection of hazard modelling datasets, CanFlood helps users connect with and manipulate such data into flood risk models.

The CanFlood plugin is NOT a flood risk model, instead it is a modelling platform with a suite of tools to aid users in building, executing, and analyzing their own models. CanFlood requires users to pre-collect and assemble the datasets that describe flood risk in their study area (see Section0_). Once analysis in CanFlood is complete, users must apply their own judgement and experience to attach the necessary context and advice to any reporting before communicating results to decision makers. CanFlood results should not be used to *make* decisions, instead they should be used to *inform* decisions along with all the other dimensions and criteria relevant to the community at risk.

.. _Section1.1:

*******************
1.1 Background
*******************

The devastation of the 2013 Southern Alberta and Toronto Floods triggered a transition in Canada from the traditional standards-based approach, where flood protection is designed for a single level-of-safety, towards a risk-based approach. This new risk-based approach recognizes that robust planning must consider vulnerability and the full range of floods that may harm a community rather than focus on a single, arbitrary, design event. Further, a risk-based view allows decision makers to quantitatively optimize mitigations for their community, helping jurisdictions with shrinking budgets spread protections further. The foundation of decisions made under a risk-based flood management is a risk assessment, which is:

   *A methodology to determine the risk by analyzing potential hazards and evaluating existing conditions of vulnerability that together could potentially harm exposed people, property, services, livelihoods and the environment on which they depend (UNISDR 2009).*

To quantify risk, modern risk assessments integrate data on the natural and built environment with predictive models. Applied in flood risk management, a risk analysis is highly sensitive to the spatial components of risk: vulnerability (what has been built where and how harmful are flood waters?) and hazard (where and how intense can flooding be?). Evaluating these components is typically accomplished with a chain of activities like data collection, processing, modelling, and post-processing to arrive at the desired risk metrics. The core components of a typical flood risk assessment are the hazard assessment to synthesize spatial exposure-likelihood data sets and a damage assessment to estimate damage to assets from the hazard assessment results, followed by the risk quantification that uses event probabilities to estimate average damages.

1.1.1 Motivation
================

Considering the limitation of existing tools, and the growing need to minimize flood harm in Canada through a better understanding of flood risk, NRCan sought to develop and maintain a flexible open-source tool tailored to Canada. Such a standardized tool will:

  • reduce the cost of individual flood risk assessments (FRA) by consolidating software development and maintenance costs;

  • increase the transparency and standardization of FRAs for improved cross study-area comparisons of risk and updating;

  • encourage communities to perform additional FRAs by reducing opacity and cost and increasing awareness;

  • facilitate and motivate the standardization and collection of flood risk related datasets; and

  • facilitate more sophisticated and stream-lined modelling.

.. _Section1.1.2:

1.1.2 Guidelines
================

**Federal Flood Mapping Guidelines Series**

“The Federal Flood Mapping Guidelines Series was developed under the leadership of the Flood Mapping Committee, a partnership between Public Safety Canada, Natural Resources Canada, Environment and Climate Change Canada, National Research Council of Canada, Defence Research and Development Canada, Canadian Armed Forces, Infrastructure Canada, and Crown Indigenous Relations and Northern Affairs Canada.” These “are a series of evergreen guidelines that will help advance flood mapping activities across Canada” (Public Safety Canada 2018). Published documents can be found with a web search for `"Federal Flood Mapping Guidelines Series.” <https://www.publicsafety.gc.ca/cnt/mrgnc-mngmnt/dsstr-prvntn-mtgtn/ndmp/fldpln-mppng-en.aspx>`__ The following are particularly relevant to CanFlood:

• Federal Flood Damage Estimation Guidelines for Buildings and Infrastructure (in development)

• Federal Flood Risk Assessment Procedures (in development)

**International Guidelines**

+------------------------+------------+----------+----------+----------+----------+----------+----------+
|Jurisdiction/ Authority |     Guideline (Reference)                                                    |          
+========================+============+==========+==========+==========+==========+==========+==========+
| United Kingdom         | Flood and coastal erosion risk management – Manual                           |
|                        | (Penning-Rowsell et al. 2013)                                                |
+------------------------+------------+----------+----------+----------+----------+----------+----------+
| United States          | Multi-Hazard Loss Estimation Methodology, Flood Model:                       |
|                        |                                                                              |
|                        | Hazus-MH MR2 Technical Manual (FEMA 2012)                                    |
|                        | Risk-Based Analysis For Flood Damage Reduction Studies (USACE 1996)          |
|                        |                                                                              |
|                        | Tying flood insurance to flood risk for low-lying structures in the          |
|                        | floodplain (National Research Council 2015)                                  |
|                        | Principles of Risk Analysis for Water Resources (IWR and USACE 2017)         |
+------------------------+------------+---------------------+----------+----------+----------+----------+


1.1.3 Risk- vs. Event-Based Models
==================================

Historically, flood management has involved decisions based on a single hypothetical, often arbitrary, ‘design event’ (e.g., 100-year discharge). This approach has left many communities under-defended and likely contributes to the rising flood losses recently seen in Canada (Frechette 2016). In response to this, modern flood management recognizes the necessity of comprehensive risk-based assessments that evaluate a range of events and their probability and consequences in management planning. CanFlood was designed to support modern risk-based management by integrating a range of flood events (e.g., 10-year, 50-year, 100-year, 200-year events) and their probabilities into risk-based models that calculate risk-metrics. However, because CanFlood calculates event-based impacts prior to any risk calculations, users can use CanFlood in event- or impact-based assessments by performing all but the final risk-calculation step.  

*******************
1.2 Intended Users
*******************

The CanFlood plugin is for users with spatial and vulnerability data desiring to perform an object-based flood risk assessment (FRA) in Canada. CanFlood is meant for flood risk practitioners with the following expertise:

   • Object-based flood risk analysis
   • QGIS (novice)

See Section1.1.2_ for a summary of guidelines and procedures related to FRAs in Canada.

.. _Section1.3:

***********************
1.3 Risk Model Levels
***********************

Flood risk analysis objectives and applications are as diverse as the communities they serve. To accommodate this wide range, CanFlood contains three types of risk models with increasing complexity as summarized in Table1-1_ and discussed in Section5.2_. To support the construction and analysis of these risk models, CanFlood also includes the ‘Build’ and ‘Results’ toolsets respectively (Section5.1_ and Section5.3_). Connecting all these together to perform an analysis is discussed in Section4.5_ and similar tutorials are provided in Section6_.

.. _Table1-1:

*Table 1-1 - CanFlood model level summaries*

.. list-table::
    :header-rows: 1
    :stub-columns: 1

    * - Analysis Level 
      - L1: Initial
      - L2: Intermediate 
      - L3: Detailed 
    * - Motivation :sup:`1`
      - Rapid FRA. desktop type appraisals: first approximations to identify areas where more detailed work is required
      - More detailed appraisals where further assessment of loss potential is warranted
      - Detailed study of potential losses and robust uncertainty quantification
    * - Workflow 
      - Section3.1_
      - Section3.2_
      - Appendix B
    * - CanFlood model tool names
      - Risk (L1)
      - Impacts (L2) and Risk (L2)
      - Risk (L3) (aka SOFDA)
    * - Data requirement 
      - low
      - medium
      - high
    * - Level of modelling effort (per asset) 
      - low
      - low
      - high
    * - Model complexity
      - low
      - medium
      - high
    * - Impact Functions
      - none (inundation only)
      - per-object
      - per-object, un-compiled
    * - Uncertainty quantification 
      - none
      - none
      - stochastic modelling
    * - PLPMs  
      - yes
      - yes
      - yes
    * - Risk Dynamics 
      - no
      - no
      - yes
    * - Asset geometry
      - point, polygon, line
      - point, polygon, line
      - point
    * - Inputs 
      - asset inventory, hazard events, DTM (optional), companion failure events (optional)
      - same as L1 plus: Impact Function Set
      - asset inventory, WSL tables, vulnerability functions (un-compiled), dynamic parameters, others
    * - Primary Outputs
      - total impacts (‘r_ttl’), per-asset impacts (‘r_passet’), risk curve plot
      - same as L1
      - exposure table, annualized impacts (summary and per asset) summary plot, others 

1. Adapted from Penning-Rowsell et al. (2019)

.. _Section1.4:

*******************
1.4 Control Files
*******************

CanFlood models are designed to write and read from small ‘Control Files’. These make it easy to build and share a specific model or scenario, and to keep a record of how the results set were generated. These also facilitate making a small change to a common input file (e.g., the asset inventory), and having this change replicated across all scenario runs. Control Files don’t contain any (large) data, only parameter values and pointers to the datasets required by a CanFlood model. Diligent and consistent file storage and naming conventions are essential for a pleasant modelling experience. Most Control File parameters and Data Files can be configured in the ‘Build’ toolset; however, some advanced parameters must be configured manually (see Section5.2_ for a full description of the Control File Parameters) (All SOFDA inputs must be built and configured manually) . The collection of model inputs and configured control file is called a ‘model package’ as shown in Figure1-1_ . More information on input files is provided in Section0_ .

.. _Figure1-1:

Figure 1-1. More information on input files is provided in :ref:`Section0` .

.. image:: /_static/intro_1_4_conrol_files.jpg

*Figure 1-1: CanFlood L2 model package and data-inputs relation diagram.*

.. |buildimage| image:: /_static/build_image.jpg
   :align: middle
   :width: 22
