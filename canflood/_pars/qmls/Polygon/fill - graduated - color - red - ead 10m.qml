<!DOCTYPE qgis PUBLIC 'http://mrcc.com/qgis.dtd' 'SYSTEM'>
<qgis styleCategories="AllStyleCategories" simplifyAlgorithm="0" labelsEnabled="1" hasScaleBasedVisibilityFlag="0" version="3.10.12-A Coruña" simplifyDrawingHints="1" simplifyDrawingTol="1" simplifyMaxScale="1" minScale="1e+08" simplifyLocal="1" maxScale="0" readOnly="0">
  <flags>
    <Identifiable>1</Identifiable>
    <Removable>1</Removable>
    <Searchable>1</Searchable>
  </flags>
  <renderer-v2 forceraster="0" type="graduatedSymbol" attr="ead" symbollevels="0" graduatedMethod="GraduatedColor" enableorderby="0">
    <ranges>
      <range label="&lt; 10,000" upper="10000.000000000000000" render="true" lower="0.000000000000000" symbol="0"/>
      <range label="&lt; 50,000" upper="50000.000000000000000" render="true" lower="10000.000000000000000" symbol="1"/>
      <range label="&lt; 200,000" upper="200000.000000000000000" render="true" lower="50000.000000000000000" symbol="2"/>
      <range label="&lt; 1,000,000" upper="1000000.000000000000000" render="true" lower="200000.000000000000000" symbol="3"/>
      <range label="&lt; 4,000,000" upper="4000000.000000000000000" render="true" lower="1000000.000000000000000" symbol="4"/>
      <range label="&lt; 10,000,000" upper="10000000.000000000000000" render="true" lower="4000000.000000000000000" symbol="5"/>
      <range label="> 10,000,000" upper="999999999.000000000000000" render="true" lower="10000000.000000000000000" symbol="6"/>
    </ranges>
    <symbols>
      <symbol name="0" type="fill" clip_to_extent="1" force_rhr="0" alpha="1">
        <layer class="LinePatternFill" enabled="1" pass="0" locked="0">
          <prop v="45" k="angle"/>
          <prop v="55,126,184,255" k="color"/>
          <prop v="2" k="distance"/>
          <prop v="3x:0,0,0,0,0,0" k="distance_map_unit_scale"/>
          <prop v="MM" k="distance_unit"/>
          <prop v="0.26" k="line_width"/>
          <prop v="3x:0,0,0,0,0,0" k="line_width_map_unit_scale"/>
          <prop v="MM" k="line_width_unit"/>
          <prop v="0" k="offset"/>
          <prop v="3x:0,0,0,0,0,0" k="offset_map_unit_scale"/>
          <prop v="MM" k="offset_unit"/>
          <prop v="3x:0,0,0,0,0,0" k="outline_width_map_unit_scale"/>
          <prop v="MM" k="outline_width_unit"/>
          <data_defined_properties>
            <Option type="Map">
              <Option name="name" type="QString" value=""/>
              <Option name="properties"/>
              <Option name="type" type="QString" value="collection"/>
            </Option>
          </data_defined_properties>
          <symbol name="@0@0" type="line" clip_to_extent="1" force_rhr="0" alpha="1">
            <layer class="SimpleLine" enabled="1" pass="0" locked="0">
              <prop v="square" k="capstyle"/>
              <prop v="5;2" k="customdash"/>
              <prop v="3x:0,0,0,0,0,0" k="customdash_map_unit_scale"/>
              <prop v="MM" k="customdash_unit"/>
              <prop v="0" k="draw_inside_polygon"/>
              <prop v="bevel" k="joinstyle"/>
              <prop v="204,204,204,255" k="line_color"/>
              <prop v="solid" k="line_style"/>
              <prop v="0.3" k="line_width"/>
              <prop v="MM" k="line_width_unit"/>
              <prop v="0" k="offset"/>
              <prop v="3x:0,0,0,0,0,0" k="offset_map_unit_scale"/>
              <prop v="MM" k="offset_unit"/>
              <prop v="0" k="ring_filter"/>
              <prop v="0" k="use_custom_dash"/>
              <prop v="3x:0,0,0,0,0,0" k="width_map_unit_scale"/>
              <data_defined_properties>
                <Option type="Map">
                  <Option name="name" type="QString" value=""/>
                  <Option name="properties"/>
                  <Option name="type" type="QString" value="collection"/>
                </Option>
              </data_defined_properties>
            </layer>
          </symbol>
        </layer>
        <layer class="SimpleLine" enabled="1" pass="0" locked="0">
          <prop v="square" k="capstyle"/>
          <prop v="5;2" k="customdash"/>
          <prop v="3x:0,0,0,0,0,0" k="customdash_map_unit_scale"/>
          <prop v="MM" k="customdash_unit"/>
          <prop v="0" k="draw_inside_polygon"/>
          <prop v="bevel" k="joinstyle"/>
          <prop v="204,204,204,255" k="line_color"/>
          <prop v="solid" k="line_style"/>
          <prop v="0.46" k="line_width"/>
          <prop v="MM" k="line_width_unit"/>
          <prop v="0" k="offset"/>
          <prop v="3x:0,0,0,0,0,0" k="offset_map_unit_scale"/>
          <prop v="MM" k="offset_unit"/>
          <prop v="0" k="ring_filter"/>
          <prop v="0" k="use_custom_dash"/>
          <prop v="3x:0,0,0,0,0,0" k="width_map_unit_scale"/>
          <data_defined_properties>
            <Option type="Map">
              <Option name="name" type="QString" value=""/>
              <Option name="properties"/>
              <Option name="type" type="QString" value="collection"/>
            </Option>
          </data_defined_properties>
        </layer>
      </symbol>
      <symbol name="1" type="fill" clip_to_extent="1" force_rhr="0" alpha="0.7">
        <layer class="SimpleFill" enabled="1" pass="0" locked="0">
          <prop v="3x:0,0,0,0,0,0" k="border_width_map_unit_scale"/>
          <prop v="255,217,217,255" k="color"/>
          <prop v="bevel" k="joinstyle"/>
          <prop v="0,0" k="offset"/>
          <prop v="3x:0,0,0,0,0,0" k="offset_map_unit_scale"/>
          <prop v="MM" k="offset_unit"/>
          <prop v="35,35,35,255" k="outline_color"/>
          <prop v="solid" k="outline_style"/>
          <prop v="0.26" k="outline_width"/>
          <prop v="MM" k="outline_width_unit"/>
          <prop v="solid" k="style"/>
          <data_defined_properties>
            <Option type="Map">
              <Option name="name" type="QString" value=""/>
              <Option name="properties"/>
              <Option name="type" type="QString" value="collection"/>
            </Option>
          </data_defined_properties>
        </layer>
      </symbol>
      <symbol name="2" type="fill" clip_to_extent="1" force_rhr="0" alpha="0.7">
        <layer class="SimpleFill" enabled="1" pass="0" locked="0">
          <prop v="3x:0,0,0,0,0,0" k="border_width_map_unit_scale"/>
          <prop v="255,178,178,255" k="color"/>
          <prop v="bevel" k="joinstyle"/>
          <prop v="0,0" k="offset"/>
          <prop v="3x:0,0,0,0,0,0" k="offset_map_unit_scale"/>
          <prop v="MM" k="offset_unit"/>
          <prop v="35,35,35,255" k="outline_color"/>
          <prop v="solid" k="outline_style"/>
          <prop v="0.26" k="outline_width"/>
          <prop v="MM" k="outline_width_unit"/>
          <prop v="solid" k="style"/>
          <data_defined_properties>
            <Option type="Map">
              <Option name="name" type="QString" value=""/>
              <Option name="properties"/>
              <Option name="type" type="QString" value="collection"/>
            </Option>
          </data_defined_properties>
        </layer>
      </symbol>
      <symbol name="3" type="fill" clip_to_extent="1" force_rhr="0" alpha="0.7">
        <layer class="SimpleFill" enabled="1" pass="0" locked="0">
          <prop v="3x:0,0,0,0,0,0" k="border_width_map_unit_scale"/>
          <prop v="255,140,140,255" k="color"/>
          <prop v="bevel" k="joinstyle"/>
          <prop v="0,0" k="offset"/>
          <prop v="3x:0,0,0,0,0,0" k="offset_map_unit_scale"/>
          <prop v="MM" k="offset_unit"/>
          <prop v="35,35,35,255" k="outline_color"/>
          <prop v="solid" k="outline_style"/>
          <prop v="0.26" k="outline_width"/>
          <prop v="MM" k="outline_width_unit"/>
          <prop v="solid" k="style"/>
          <data_defined_properties>
            <Option type="Map">
              <Option name="name" type="QString" value=""/>
              <Option name="properties"/>
              <Option name="type" type="QString" value="collection"/>
            </Option>
          </data_defined_properties>
        </layer>
      </symbol>
      <symbol name="4" type="fill" clip_to_extent="1" force_rhr="0" alpha="0.7">
        <layer class="SimpleFill" enabled="1" pass="0" locked="0">
          <prop v="3x:0,0,0,0,0,0" k="border_width_map_unit_scale"/>
          <prop v="255,102,102,255" k="color"/>
          <prop v="bevel" k="joinstyle"/>
          <prop v="0,0" k="offset"/>
          <prop v="3x:0,0,0,0,0,0" k="offset_map_unit_scale"/>
          <prop v="MM" k="offset_unit"/>
          <prop v="35,35,35,255" k="outline_color"/>
          <prop v="solid" k="outline_style"/>
          <prop v="0.26" k="outline_width"/>
          <prop v="MM" k="outline_width_unit"/>
          <prop v="solid" k="style"/>
          <data_defined_properties>
            <Option type="Map">
              <Option name="name" type="QString" value=""/>
              <Option name="properties"/>
              <Option name="type" type="QString" value="collection"/>
            </Option>
          </data_defined_properties>
        </layer>
      </symbol>
      <symbol name="5" type="fill" clip_to_extent="1" force_rhr="0" alpha="0.7">
        <layer class="SimpleFill" enabled="1" pass="0" locked="0">
          <prop v="3x:0,0,0,0,0,0" k="border_width_map_unit_scale"/>
          <prop v="255,51,51,255" k="color"/>
          <prop v="bevel" k="joinstyle"/>
          <prop v="0,0" k="offset"/>
          <prop v="3x:0,0,0,0,0,0" k="offset_map_unit_scale"/>
          <prop v="MM" k="offset_unit"/>
          <prop v="35,35,35,255" k="outline_color"/>
          <prop v="solid" k="outline_style"/>
          <prop v="0.26" k="outline_width"/>
          <prop v="MM" k="outline_width_unit"/>
          <prop v="solid" k="style"/>
          <data_defined_properties>
            <Option type="Map">
              <Option name="name" type="QString" value=""/>
              <Option name="properties"/>
              <Option name="type" type="QString" value="collection"/>
            </Option>
          </data_defined_properties>
        </layer>
      </symbol>
      <symbol name="6" type="fill" clip_to_extent="1" force_rhr="0" alpha="0.7">
        <layer class="SimpleFill" enabled="1" pass="0" locked="0">
          <prop v="3x:0,0,0,0,0,0" k="border_width_map_unit_scale"/>
          <prop v="255,0,0,255" k="color"/>
          <prop v="bevel" k="joinstyle"/>
          <prop v="0,0" k="offset"/>
          <prop v="3x:0,0,0,0,0,0" k="offset_map_unit_scale"/>
          <prop v="MM" k="offset_unit"/>
          <prop v="35,35,35,255" k="outline_color"/>
          <prop v="solid" k="outline_style"/>
          <prop v="0.26" k="outline_width"/>
          <prop v="MM" k="outline_width_unit"/>
          <prop v="solid" k="style"/>
          <data_defined_properties>
            <Option type="Map">
              <Option name="name" type="QString" value=""/>
              <Option name="properties"/>
              <Option name="type" type="QString" value="collection"/>
            </Option>
          </data_defined_properties>
        </layer>
      </symbol>
    </symbols>
    <source-symbol>
      <symbol name="0" type="fill" clip_to_extent="1" force_rhr="0" alpha="0.7">
        <layer class="SimpleFill" enabled="1" pass="0" locked="0">
          <prop v="3x:0,0,0,0,0,0" k="border_width_map_unit_scale"/>
          <prop v="229,182,54,255" k="color"/>
          <prop v="bevel" k="joinstyle"/>
          <prop v="0,0" k="offset"/>
          <prop v="3x:0,0,0,0,0,0" k="offset_map_unit_scale"/>
          <prop v="MM" k="offset_unit"/>
          <prop v="35,35,35,255" k="outline_color"/>
          <prop v="solid" k="outline_style"/>
          <prop v="0.26" k="outline_width"/>
          <prop v="MM" k="outline_width_unit"/>
          <prop v="solid" k="style"/>
          <data_defined_properties>
            <Option type="Map">
              <Option name="name" type="QString" value=""/>
              <Option name="properties"/>
              <Option name="type" type="QString" value="collection"/>
            </Option>
          </data_defined_properties>
        </layer>
      </symbol>
    </source-symbol>
    <colorramp name="[source]" type="gradient">
      <prop v="255,255,255,255" k="color1"/>
      <prop v="255,0,0,255" k="color2"/>
      <prop v="0" k="discrete"/>
      <prop v="gradient" k="rampType"/>
    </colorramp>
    <classificationMethod id="EqualInterval">
      <symmetricMode symmetrypoint="0" enabled="0" astride="0"/>
      <labelFormat format="%1 - %2 " trimtrailingzeroes="1" labelprecision="4"/>
      <extraInformation/>
    </classificationMethod>
    <rotation/>
    <sizescale/>
  </renderer-v2>
  <labeling type="simple">
    <settings calloutType="simple">
      <text-style fontStrikeout="0" textColor="0,0,0,255" namedStyle="Regular" blendMode="0" useSubstitutions="0" textOrientation="horizontal" fontLetterSpacing="0" fontSize="8" fontUnderline="0" fieldName="concat('$',format_number(&quot;ead&quot;,0))" textOpacity="1" fontFamily="MS Shell Dlg 2" isExpression="1" fontSizeUnit="Point" previewBkgrdColor="255,255,255,255" multilineHeight="1" fontCapitals="0" fontWeight="50" fontItalic="0" fontKerning="1" fontSizeMapUnitScale="3x:0,0,0,0,0,0" fontWordSpacing="0">
        <text-buffer bufferBlendMode="0" bufferSize="1" bufferJoinStyle="128" bufferDraw="0" bufferColor="255,255,255,255" bufferSizeMapUnitScale="3x:0,0,0,0,0,0" bufferNoFill="1" bufferOpacity="1" bufferSizeUnits="MM"/>
        <background shapeRadiiY="0" shapeSizeType="0" shapeOpacity="1" shapeDraw="0" shapeBorderColor="128,128,128,255" shapeType="0" shapeRadiiX="0" shapeOffsetY="0" shapeFillColor="255,255,255,255" shapeSizeUnit="MM" shapeJoinStyle="64" shapeSizeY="0" shapeOffsetUnit="MM" shapeRadiiMapUnitScale="3x:0,0,0,0,0,0" shapeRotationType="0" shapeBorderWidth="0" shapeOffsetX="0" shapeRotation="0" shapeOffsetMapUnitScale="3x:0,0,0,0,0,0" shapeBorderWidthMapUnitScale="3x:0,0,0,0,0,0" shapeRadiiUnit="MM" shapeBorderWidthUnit="MM" shapeSizeX="0" shapeSVGFile="" shapeSizeMapUnitScale="3x:0,0,0,0,0,0" shapeBlendMode="0">
          <symbol name="markerSymbol" type="marker" clip_to_extent="1" force_rhr="0" alpha="1">
            <layer class="SimpleMarker" enabled="1" pass="0" locked="0">
              <prop v="0" k="angle"/>
              <prop v="231,113,72,255" k="color"/>
              <prop v="1" k="horizontal_anchor_point"/>
              <prop v="bevel" k="joinstyle"/>
              <prop v="circle" k="name"/>
              <prop v="0,0" k="offset"/>
              <prop v="3x:0,0,0,0,0,0" k="offset_map_unit_scale"/>
              <prop v="MM" k="offset_unit"/>
              <prop v="35,35,35,255" k="outline_color"/>
              <prop v="solid" k="outline_style"/>
              <prop v="0" k="outline_width"/>
              <prop v="3x:0,0,0,0,0,0" k="outline_width_map_unit_scale"/>
              <prop v="MM" k="outline_width_unit"/>
              <prop v="diameter" k="scale_method"/>
              <prop v="2" k="size"/>
              <prop v="3x:0,0,0,0,0,0" k="size_map_unit_scale"/>
              <prop v="MM" k="size_unit"/>
              <prop v="1" k="vertical_anchor_point"/>
              <data_defined_properties>
                <Option type="Map">
                  <Option name="name" type="QString" value=""/>
                  <Option name="properties"/>
                  <Option name="type" type="QString" value="collection"/>
                </Option>
              </data_defined_properties>
            </layer>
          </symbol>
        </background>
        <shadow shadowScale="100" shadowColor="0,0,0,255" shadowOffsetGlobal="1" shadowRadius="1.5" shadowRadiusUnit="MM" shadowRadiusAlphaOnly="0" shadowBlendMode="6" shadowOffsetUnit="MM" shadowOffsetMapUnitScale="3x:0,0,0,0,0,0" shadowOffsetAngle="135" shadowOffsetDist="1" shadowRadiusMapUnitScale="3x:0,0,0,0,0,0" shadowDraw="0" shadowOpacity="0.7" shadowUnder="0"/>
        <dd_properties>
          <Option type="Map">
            <Option name="name" type="QString" value=""/>
            <Option name="properties"/>
            <Option name="type" type="QString" value="collection"/>
          </Option>
        </dd_properties>
        <substitutions/>
      </text-style>
      <text-format plussign="0" wrapChar="" reverseDirectionSymbol="0" useMaxLineLengthForAutoWrap="1" formatNumbers="0" autoWrapLength="0" multilineAlign="0" addDirectionSymbol="0" leftDirectionSymbol="&lt;" placeDirectionSymbol="0" decimals="3" rightDirectionSymbol=">"/>
      <placement quadOffset="4" centroidInside="0" predefinedPositionOrder="TR,TL,BR,BL,R,L,TSR,BSR" overrunDistanceMapUnitScale="3x:0,0,0,0,0,0" yOffset="0" rotationAngle="0" placementFlags="10" offsetType="0" distUnits="MM" maxCurvedCharAngleOut="-25" priority="5" layerType="PolygonGeometry" xOffset="0" dist="0" maxCurvedCharAngleIn="25" repeatDistance="0" repeatDistanceUnits="MM" fitInPolygonOnly="0" overrunDistance="0" offsetUnits="MM" centroidWhole="0" placement="5" overrunDistanceUnit="MM" preserveRotation="1" distMapUnitScale="3x:0,0,0,0,0,0" geometryGeneratorType="PointGeometry" geometryGenerator="" labelOffsetMapUnitScale="3x:0,0,0,0,0,0" repeatDistanceMapUnitScale="3x:0,0,0,0,0,0" geometryGeneratorEnabled="0"/>
      <rendering scaleMax="0" scaleMin="0" scaleVisibility="0" zIndex="0" obstacleFactor="1" upsidedownLabels="0" fontMaxPixelSize="10000" labelPerPart="0" fontLimitPixelSize="0" mergeLines="0" obstacle="0" maxNumLabels="2000" displayAll="1" drawLabels="1" obstacleType="0" fontMinPixelSize="3" minFeatureSize="0" limitNumLabels="0"/>
      <dd_properties>
        <Option type="Map">
          <Option name="name" type="QString" value=""/>
          <Option name="properties"/>
          <Option name="type" type="QString" value="collection"/>
        </Option>
      </dd_properties>
      <callout type="simple">
        <Option type="Map">
          <Option name="anchorPoint" type="QString" value="pole_of_inaccessibility"/>
          <Option name="ddProperties" type="Map">
            <Option name="name" type="QString" value=""/>
            <Option name="properties"/>
            <Option name="type" type="QString" value="collection"/>
          </Option>
          <Option name="drawToAllParts" type="bool" value="false"/>
          <Option name="enabled" type="QString" value="0"/>
          <Option name="lineSymbol" type="QString" value="&lt;symbol name=&quot;symbol&quot; type=&quot;line&quot; clip_to_extent=&quot;1&quot; force_rhr=&quot;0&quot; alpha=&quot;1&quot;>&lt;layer class=&quot;SimpleLine&quot; enabled=&quot;1&quot; pass=&quot;0&quot; locked=&quot;0&quot;>&lt;prop v=&quot;square&quot; k=&quot;capstyle&quot;/>&lt;prop v=&quot;5;2&quot; k=&quot;customdash&quot;/>&lt;prop v=&quot;3x:0,0,0,0,0,0&quot; k=&quot;customdash_map_unit_scale&quot;/>&lt;prop v=&quot;MM&quot; k=&quot;customdash_unit&quot;/>&lt;prop v=&quot;0&quot; k=&quot;draw_inside_polygon&quot;/>&lt;prop v=&quot;bevel&quot; k=&quot;joinstyle&quot;/>&lt;prop v=&quot;60,60,60,255&quot; k=&quot;line_color&quot;/>&lt;prop v=&quot;solid&quot; k=&quot;line_style&quot;/>&lt;prop v=&quot;0.3&quot; k=&quot;line_width&quot;/>&lt;prop v=&quot;MM&quot; k=&quot;line_width_unit&quot;/>&lt;prop v=&quot;0&quot; k=&quot;offset&quot;/>&lt;prop v=&quot;3x:0,0,0,0,0,0&quot; k=&quot;offset_map_unit_scale&quot;/>&lt;prop v=&quot;MM&quot; k=&quot;offset_unit&quot;/>&lt;prop v=&quot;0&quot; k=&quot;ring_filter&quot;/>&lt;prop v=&quot;0&quot; k=&quot;use_custom_dash&quot;/>&lt;prop v=&quot;3x:0,0,0,0,0,0&quot; k=&quot;width_map_unit_scale&quot;/>&lt;data_defined_properties>&lt;Option type=&quot;Map&quot;>&lt;Option name=&quot;name&quot; type=&quot;QString&quot; value=&quot;&quot;/>&lt;Option name=&quot;properties&quot;/>&lt;Option name=&quot;type&quot; type=&quot;QString&quot; value=&quot;collection&quot;/>&lt;/Option>&lt;/data_defined_properties>&lt;/layer>&lt;/symbol>"/>
          <Option name="minLength" type="double" value="0"/>
          <Option name="minLengthMapUnitScale" type="QString" value="3x:0,0,0,0,0,0"/>
          <Option name="minLengthUnit" type="QString" value="MM"/>
          <Option name="offsetFromAnchor" type="double" value="0"/>
          <Option name="offsetFromAnchorMapUnitScale" type="QString" value="3x:0,0,0,0,0,0"/>
          <Option name="offsetFromAnchorUnit" type="QString" value="MM"/>
          <Option name="offsetFromLabel" type="double" value="0"/>
          <Option name="offsetFromLabelMapUnitScale" type="QString" value="3x:0,0,0,0,0,0"/>
          <Option name="offsetFromLabelUnit" type="QString" value="MM"/>
        </Option>
      </callout>
    </settings>
  </labeling>
  <customproperties/>
  <blendMode>0</blendMode>
  <featureBlendMode>0</featureBlendMode>
  <layerOpacity>1</layerOpacity>
  <geometryOptions removeDuplicateNodes="0" geometryPrecision="0">
    <activeChecks type="StringList">
      <Option type="QString" value=""/>
    </activeChecks>
    <checkConfiguration/>
  </geometryOptions>
  <fieldConfiguration>
    <field name="xid">
      <editWidget type="">
        <config>
          <Option/>
        </config>
      </editWidget>
    </field>
    <field name="ari_00002">
      <editWidget type="">
        <config>
          <Option/>
        </config>
      </editWidget>
    </field>
    <field name="ari_00050">
      <editWidget type="">
        <config>
          <Option/>
        </config>
      </editWidget>
    </field>
    <field name="ari_00100">
      <editWidget type="">
        <config>
          <Option/>
        </config>
      </editWidget>
    </field>
    <field name="ari_00200">
      <editWidget type="">
        <config>
          <Option/>
        </config>
      </editWidget>
    </field>
    <field name="ari_01000">
      <editWidget type="">
        <config>
          <Option/>
        </config>
      </editWidget>
    </field>
    <field name="ari_10000">
      <editWidget type="">
        <config>
          <Option/>
        </config>
      </editWidget>
    </field>
    <field name="ead">
      <editWidget type="">
        <config>
          <Option/>
        </config>
      </editWidget>
    </field>
    <field name="f0_scale">
      <editWidget type="">
        <config>
          <Option/>
        </config>
      </editWidget>
    </field>
    <field name="f0_elv">
      <editWidget type="">
        <config>
          <Option/>
        </config>
      </editWidget>
    </field>
  </fieldConfiguration>
  <aliases>
    <alias index="0" name="" field="xid"/>
    <alias index="1" name="" field="ari_00002"/>
    <alias index="2" name="" field="ari_00050"/>
    <alias index="3" name="" field="ari_00100"/>
    <alias index="4" name="" field="ari_00200"/>
    <alias index="5" name="" field="ari_01000"/>
    <alias index="6" name="" field="ari_10000"/>
    <alias index="7" name="" field="ead"/>
    <alias index="8" name="" field="f0_scale"/>
    <alias index="9" name="" field="f0_elv"/>
  </aliases>
  <excludeAttributesWMS/>
  <excludeAttributesWFS/>
  <defaults>
    <default field="xid" expression="" applyOnUpdate="0"/>
    <default field="ari_00002" expression="" applyOnUpdate="0"/>
    <default field="ari_00050" expression="" applyOnUpdate="0"/>
    <default field="ari_00100" expression="" applyOnUpdate="0"/>
    <default field="ari_00200" expression="" applyOnUpdate="0"/>
    <default field="ari_01000" expression="" applyOnUpdate="0"/>
    <default field="ari_10000" expression="" applyOnUpdate="0"/>
    <default field="ead" expression="" applyOnUpdate="0"/>
    <default field="f0_scale" expression="" applyOnUpdate="0"/>
    <default field="f0_elv" expression="" applyOnUpdate="0"/>
  </defaults>
  <constraints>
    <constraint notnull_strength="0" constraints="0" field="xid" exp_strength="0" unique_strength="0"/>
    <constraint notnull_strength="0" constraints="0" field="ari_00002" exp_strength="0" unique_strength="0"/>
    <constraint notnull_strength="0" constraints="0" field="ari_00050" exp_strength="0" unique_strength="0"/>
    <constraint notnull_strength="0" constraints="0" field="ari_00100" exp_strength="0" unique_strength="0"/>
    <constraint notnull_strength="0" constraints="0" field="ari_00200" exp_strength="0" unique_strength="0"/>
    <constraint notnull_strength="0" constraints="0" field="ari_01000" exp_strength="0" unique_strength="0"/>
    <constraint notnull_strength="0" constraints="0" field="ari_10000" exp_strength="0" unique_strength="0"/>
    <constraint notnull_strength="0" constraints="0" field="ead" exp_strength="0" unique_strength="0"/>
    <constraint notnull_strength="0" constraints="0" field="f0_scale" exp_strength="0" unique_strength="0"/>
    <constraint notnull_strength="0" constraints="0" field="f0_elv" exp_strength="0" unique_strength="0"/>
  </constraints>
  <constraintExpressions>
    <constraint field="xid" exp="" desc=""/>
    <constraint field="ari_00002" exp="" desc=""/>
    <constraint field="ari_00050" exp="" desc=""/>
    <constraint field="ari_00100" exp="" desc=""/>
    <constraint field="ari_00200" exp="" desc=""/>
    <constraint field="ari_01000" exp="" desc=""/>
    <constraint field="ari_10000" exp="" desc=""/>
    <constraint field="ead" exp="" desc=""/>
    <constraint field="f0_scale" exp="" desc=""/>
    <constraint field="f0_elv" exp="" desc=""/>
  </constraintExpressions>
  <expressionfields/>
  <attributeactions>
    <defaultAction key="Canvas" value="{00000000-0000-0000-0000-000000000000}"/>
  </attributeactions>
  <attributetableconfig actionWidgetStyle="dropDown" sortExpression="" sortOrder="0">
    <columns/>
  </attributetableconfig>
  <conditionalstyles>
    <rowstyles/>
    <fieldstyles/>
  </conditionalstyles>
  <storedexpressions/>
  <editform tolerant="1"></editform>
  <editforminit/>
  <editforminitcodesource>0</editforminitcodesource>
  <editforminitfilepath></editforminitfilepath>
  <editforminitcode><![CDATA[]]></editforminitcode>
  <featformsuppress>0</featformsuppress>
  <editorlayout>generatedlayout</editorlayout>
  <editable/>
  <labelOnTop/>
  <widgets/>
  <previewExpression></previewExpression>
  <mapTip></mapTip>
  <layerGeometryType>2</layerGeometryType>
</qgis>
