# Project state-filter development specification

## General Description
- Project state-filter is a command line application designed to take as a required input a single US state name and return a list of data package identifiers from the Environmental Data Initiative data repository based on metadata defined in each data package using spatial metadata and semantic metadata.
- Optional inputs may inlcude:
  - Organizational name.
  - Geographic name place name.
  - Keywords.
  - Abstract.
- Each option input corresponds to a section of semantic metadata.

## Data package discovery
- Data package discovery is based on an EDI PASTA REST API: "https://pasta.lternet.edu/package/search/eml?<query_string>"
- The query_string is based on a typical Solr 8.3 query expression.
- An example query_string follows: "https://pasta.lternet.edu/package/search/eml?defType=edismax&q=Vernberg&fq=-scope:ecotrends&fq=-scope:lter-landsat*&fl=*\&sort=score,desc&sort=packageid,asc&debug=false&start=0&rows=10" 
- A query result is returned as XML:
```
<resultset numFound='3' start='0' rows='10'>
    <document>
        <abstract>This data package consists of Daily Water Sample Parameter,...</abstract>
        <begindate>1981</begindate>
        <doi>doi:10.6073/pasta/2b809c045fdd74a7cc12e8f31fc191eb</doi>
        <enddate>1993</enddate>
        <funding></funding>
        <geographicdescription>North Inlet encompasses about 2,630 hectares of tidal...</geographicdescription>
        <id>knb-lter-nin.8</id>
        <docid>knb-lter-nin.8</docid>
        <methods></methods>
        <packageid>knb-lter-nin.8.1</packageid>
        <pubdate>2013</pubdate>
        <responsibleParties>NIN&#x2d;LTER
            Vernberg, John
            Blood, Elizabeth
            Gardner, Robert
        </responsibleParties>
        <scope>knb-lter-nin</scope>
        <singledate></singledate>
        <site>nin</site>
        <taxonomic></taxonomic>
        <title>Suspended Sediment&#x2e; Daily Water Sample Parameter&#x2c; and Sediment...</title>
        <authors>
            <author>Vernberg, John</author>
            <author>Blood, Elizabeth</author>
            <author>Gardner, Robert</author>
        </authors>
        <spatialCoverage>
            <coordinates>-79.2936 33.1925 -79.1042 33.357</coordinates>
        </spatialCoverage>
        <sources>
        </sources>
        <keywords>
            <keyword>North Inlet Estuary</keyword>
            <keyword>Baruch Institute</keyword>
            <keyword>Georgetown, South Carolina</keyword>
            <keyword>sediment</keyword>
            <keyword>substances</keyword>
            <keyword>ecology</keyword>
            <keyword>community dynamics</keyword>
            <keyword>populations</keyword>
        </keywords>
        <organizations>
            <organization>NIN&#x2d;LTER</organization>
        </organizations>
        <timescales>
        </timescales>
    </document>
</resultset>
```
- The query_string is formed with semantic relevant metadata that correspond to the input options. The list of possible query categories follows:

### Single-value Fields:
    1. abstract
    1. begindate
    1. doi
    1. enddate
    1. funding
    1. geographicdescription
    1. id
    1. methods
    1. packageid
    1. pubdate
    1. responsibleParties
    1. scope
    1. singledate
    1. site
    1. taxonomic
    1. title

### Multi-value Fields
    1. author
    1. coordinates
    1. keyword
    1. organization
    1. projectTitle
    1. relatedProjectTitle
    1. timescale

- Of particular interest will be the coordinates for spatial filtering and abstract, geographicdescription, responsibleParties, author, keyword, organization, and projectTitle for semantic filtering.
- The packageId will be used to mark relevant data package identifiers.

## Discovery Strategy
- A preliminary discovery search should be based on two criteria:
    1. A bounding box of the state.
    2. Semantic input options.
- After the preliminary search, a higher precision filtering of the returned result XML should be performed by including:
    1. Only data package coordinates that are fully contained within the state or
    2. Data package coordinates that are either fully contained within the state or cross the state boundary.
- Note that bounding boxes of each state should be loaded from a data file (preferrably json) containing the values of maxLat, minLat, maxLon, minLon in the order expected by Solr.

## Coding Requirements
- Use the most recent requirements compatible Python.
- Use pixi for package management. There already exists a pyproject.toml file as a starting point.
- Use click for command the line interface.
- Use 'CONTEXT_SETTINGS = dict(help_option_names=["-h", "--help"])' when setting up click.
- Because we are dealing with XML, XML parsers should be secure.
- Tests should be written for all functions.
- Spatial filtering should use spatial coordinates (latitude/longitude boundaries) defined in the search result XML and should be evaluated against simplified US State polygon boundaries using shapely.geometry.Polygon and shapely.geometry.Point.
- The geospatial boundary matching must handle multi-polygons (e.g., states with islands like Hawaii or Alaska) and validate coordinates within range [-90, 90] for latitude and [-180, 180] for longitude.
- To safeguard the application, direct use of standard Python xml.etree or raw lxml on untrusted inputs is strictly prohibited. All XML parsing must pass through defusedxml wrappers or explicitly disable external entity loading.
- Linting: Enforced via ruff check with import sorting enabled.
- Type Hinting: Mandatory on all public and private function signatures. Union types must use the modern TypeA | TypeB syntax.
- Docstrings: Google-style docstrings are required for all non-obvious modules, classes, and functions.
