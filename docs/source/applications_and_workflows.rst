.. _applications_and_workflows:

==============================
3. Applications and Workflows
==============================

The CanFlood plugin holds a collection of tools designed to support flood risk modellers with range of common tasks. To accomplish this, CanFlood is flexible: allowing users to link together whichever tools and sequences are needed to complete the task at hand. Performing a flood risk assessment using CanFlood requires expertise in flood risk modelling, some procedures like those referenced in Section1.1.2_ , and generally employs the following steps:

  1. Identifying the objectives, scope, and purpose of the assessment.
  2. Selecting the appropriate CanFlood model level (Section1.3_) then identifying the necessary input data.
  3. Collecting and preparing the necessary input data (Section0_).
  4. Building the CanFlood model package (see below).
  5. Running the CanFlood model package using the appropriate model tool (Section5.2_).
  6. Using CanFlood’s ‘Results’ tools to prepare diagrams and maps (Section5.3_).
  7. Evaluating, documenting, and communicating the results, context, and uncertainty.

As noted in the section references, many of these steps must be performed outside the CanFlood platform.

**Building Models**

Most workflows in CanFlood require the user to employ a similar sequence of the ‘Build’ tools described in Section5.1_ to prepare the CanFlood model package (Figure1-1_) from the input data. Figure3-1_ shows a typical workflow from ‘Setup’ to ‘Validation’. Whether or not to include the optional steps shown on the diagram will depend on the following:

  • *Risk model level*: L2 models require vulnerability functions (‘curves’) (see Section3.2_).
  • *Defense failure*: L1 or L2 models incorporating some protection failure require companion failure events (failure   rasters and failure polygons) (see Section3.3_).
  • *Asset heights*: L1 or L2 models incorporating asset inventories with object height data relative to ground require ground elevations data (‘gels’).
  • *Exposure type*: L1 or L2 models with non-point geometry assets evaluating exposure as a percentage of inundation (Section5.1.3_) require a DTM layer.

.. _Figure3-1:

.. image:: /_static/app_workflow_build_model.jpg

*Figure 3-1: Typical model construction workflow using CanFlood’s ‘Build’ tools from ‘Setup’ to ‘Validation’. Data inputs are described in Section 0 while tools and outputs are described in*  Section5.1_ 

More information and additional tools to support model construction are provided in Section5.1_ .

The remainder of this section summarizes some typical analysis types or workflows employing the risk models summarized in Section1.3_ and discussed in detail in Section5.2_ . All these workflows are risk-based, in that they incorporate a wide-range of event probabilities and calculate risk-metrics. The tutorials in Section 6 provide step-by-step instructions and accompanying input data to demonstrate these workflows.

.. _Section3.1:

*****************************************
3.1. Risk (L1) Exposure-Based Assessment
*****************************************

Exposure-based (L1) assessments quantify the probability of binary exposure of assets to flooding (wet vs. dry). This can be useful for initial assessments, where resources and data are limited, to identify areas for further study. In CanFlood, this is accomplished by collecting data, building a Risk (L1) model, running the model, and evaluating the results. Unlike vulnerability-based assessments (L2, Section3.2_), exposure-based (L1) assessments do not capture the influence of flood depth on risk. In other words, a house with some ponding in the yard would be counted the same as a house fully under-water. However, exposure-based (L1) assessments can be used to estimate additional risk-metrics through application of CanFlood’s scaling parameters (e.g., estimating crop-loss by multiplying the area inundated by some loss/area constant). Exposure-based (L1) assessments can incorporate an assessment of defense failure if exposure probability data is available (Section3.3_). Figure3-1_ and Figure3-2_ summarize a typical Risk (L1) workflow. For more information on the Risk (L1) model, see Section5.2.1_.

.. _Figure3-2:

.. image:: /_static/app_wrkflw_3_1_risk_ecp.jpg

*Figure 3-2: Typical Risk (L1) workflow (post- model construction).*

.. _Section3.2:

**********************************************
3.2. Risk (L2) Vulnerability-Based Assessment
**********************************************

Vulnerability-based (L2) assessments quantify the risk of some flood impacts to assets where the impact can be related to depth. Risk models that consider vulnerability as a function of flood depth are commonly used to evaluate flood risk to buildings, building contents, and infrastructure. In CanFlood, such an assessment is conducted by collecting data, constructing or collecting vulnerability functions, building a Risk (L2) model, running said model, then evaluating the results. Often the most challenging element of this process is the collection or construction of vulnerability functions (Section4.3_) which future versions of CanFlood may provide support for. Vulnerability-based (L2) assessments generally incorporate an assessment of defense failure (Section3.3_). Figure3-1_ and Figure3-3_ summarize a typical Risk (L2) workflow. For more information on the Risk (L2) model, see Section5.2.3_.

.. _Figure3-3:

.. image:: /_static/app_wrkflw_3_2_vuln.jpg

*Figure 3-3: Typical Risk (L2) workflow (post-model construction).*

.. _Section3.3:

**********************
3.3. Defense Failure
**********************

Many developed areas in Canada rely on some form of flood defense infrastructure (e.g., levees or drainage pumps) to reduce the exposure of assets. Any such infrastructure has the potential to fail during a flood event. Ignoring this failure potential (P :sub:`fail` =0) will underestimate the real flood risk in an area (negative model bias). Assuming such infrastructure will always fail (P :sub:`fail` =1) can drastically overestimate flood risk (positive model bias). Either assumption will reduce confidence in the model and the quality of any flood management decisions made from it. In many areas in Canada, flood protection plays such a significant role in exposure mechanics that a binary treatment of failure probability (P :sub:`fail` = 0 or 1) would render the model’s calculated risk metric useless. Recognizing the importance of flood protection infrastructure in Canadian flood risk management, CanFlood Risk (L1) and Risk (L2) workflows facilitate the incorporation of defense failure into risk calculations.

A common application of this capability is the incorporation of levee fragility into a risk model. Often such study areas will have groups of levee-protected assets, where each asset is vulnerable to a breach point anywhere along a levee ring. This situation can be analyzed by discretizing the levee into segments, estimating the influence area of a breach along each segment (for event *j*), estimating the conditional probability of that breach occurring (during event *j*), and developing hazard rasters for the breach conditions. Qualified hydrotechnical and geotechnical professionals should be engaged to perform this analysis and generate the inputs required by CanFlood as summarized in Section4.2_.

3.3.1. Workflow
================

Defense failure is incorporated into risk calculations during CanFlood’s Risk (L1) and Risk (L2) workflows with the following general steps:

  1) Collect the set of hazard event rasters (Section4.2_) and dike profile, fragility, and influence area information (Section4.5_).

  2) Calculate the dike failure probability of each hazard event and map it onto the dike influence area using the ‘Dike Fragility Mapper’ tool (Section5.4.1_) to obtain the ‘failure polygon’ set.

  3) From the ‘failure polygons’, extract, resolve, and assign conditional failure probabilities for each failure event into the resolved exposure probabilities (‘exlikes’) dataset using the ‘Conditional P’ tool (Section5.1.5_).

  4) Execute the Risk (L1) or Risk (L2) model to employ CanFlood’s algorithms to calculate expected values with defense failure (Section5.2.3_ *Events with Failure*).

Figure3-4_ summarizes CanFlood’s full expected value algorithm.

.. _figure3-4:

.. image:: /_static/app_wrkflw_3_3_1_wrkflw.jpg

*Figure 3-4: CanFlood's Risk (L1 and L2) tool expected value (E(X)) calculation algorithm*

3.3.2. Event Relations
=======================

To calculate expected values (in more complex models), the application of both the ‘Conditional P’ tool and the risk models requires accounting for the relationship between the events supplied by the user. In other words, when multiple failures are specified, one must specify how those failures should/should-not be combined. Calculating and incorporating failure correlations between elements in a defense system requires a sophisticated and mechanistic understanding of the system that is beyond the scope of CanFlood. As an alternative approximation, CanFlood includes two basic assumptions, summarized in Figure3-5_, for the relationship between failure elements. These alternate assumptions are provided to allow the user to test the sensitivity of the model to failure element correlations; if the model is found to have a high sensitivity to this parameter, more sophisticated defense system analysis should be pursued.

.. _Figure3-5:

.. image:: /_static/app_wrkflw_3_3_2_event_relations.jpg

*Figure 3-5: Example probability space diagram showing two events either [left] independent or [right] mutually exclusive where ‘P(o)’ is the probability of no failures.*
