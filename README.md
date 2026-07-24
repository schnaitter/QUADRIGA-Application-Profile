# QUADRIGA Application Profile

[![DOI](https://zenodo.org/badge/1007838017.svg)](https://doi.org/10.5281/zenodo.18184772)

**Table of Contents**

- [QUADRIGA Application Profile](#quadriga-application-profile)
  - [About This Repository](#about-this-repository)
  - [Structure of the QAP](#structure-of-the-qap)
    - [Canonical order of the elements in `metadata.yml`](#canonical-order-of-the-elements-in-metadatayml)
    - [Diagrams](#diagrams)
  - [Usage](#usage)
    - [Creating Metadata Files](#creating-metadata-files)
    - [Vocabulary Mappings (x-mappings)](#vocabulary-mappings-x-mappings)
      - [Structure](#structure)
      - [Target Vocabularies](#target-vocabularies)
      - [SKOS Relation Types](#skos-relation-types)
      - [Meta-Schema](#meta-schema)
  - [Documentation](#documentation)

The QUADRIGA Application Profile (QAP) is a JSON-Schema designed for describing
Open Educational Resources (OER) in German academic contexts. It provides
structured metadata for learning materials, integrating competency frameworks,
Bloom's taxonomy, and multilingual support to enable comprehensive resource
description and discovery. It is used primarily withing QUADRIGA as ground
truth within a Jupyter Book repository and to allow the Navigator to ingest
this metadata for retrieval purposes.

The application profile emphasizes semantic web compatibility through [Dublin
Core](https://www.dublincore.org/specifications/dublin-core/dcmi-terms/) and
[Schema.org](https://schema.org/) mappings, while supporting flexible person
representation, learning objectives tracking, and quality assurance workflows
tailored for educational content creation and management.

## About This Repository

This repository contains the complete QUADRIGA application profile (QAP)
definition split into modular JSON files for maintainability. It features a
versioning system with a `latest/` symlink pointing to the current version,
automated HTML documentation generation via GitHub Actions, and deployment to
GitHub Pages for easy access and reference.

**Entry Point:** `schema.json`

**Licensing:** The QAP is licensed under CC0 (see `LICENSE-QAP.txt`). Any
code in this repository is licensed under MIT (see `LICENSE-CODE.txt`).

**Archiving:** The QAP is archived on Zenodo for long-term preservation and
citable DOI assignment. Zenodo metadata is maintained in `.zenodo.json`.

## Structure of the QAP

The QAP describes educational resources with the following key components:

- **Basic metadata**: Title, description, identifiers, publication dates, and
  versioning
- **Authors and contributors**: Structured person information with
  [ORCID](https://orcid.org/) and [CRediT](https://credit.niso.org) support
- **Content organization**: Chapter-based structure with individual learning
  objectives
- **Competency mapping**: Integration with [QUADRIGA data literacy
  framework](https://doi.org/10.5281/zenodo.14747822), data flow categories,
  and Bloom's taxonomy
- **Context information**: Discipline, target groups, and research object types

See [`examples/minimal_metadata.yml`](./examples/minimal_metadata.yml) for a
minimal example showing how these elements work together to describe an
educational resource.

### Canonical order of the elements in `quadriga-metadata.yml`

The following order of elements is recommended (required fields have an
asterisk after their name):

```
- title*
- authors*
  - (definition of each author)
    - family-names*
    - given-names*
- keywords*
- description*
- table-of-contents*
- discipline*
- research-object-type*
- target-group*
- time-required*
- language*
- contributors*
  - (definition of each contributor)
    - family-names*
    - given-names*
- identifier*
- git*
- url*
- prerequisites
- used-tools
  - (definition for each tool)
    - name
    - url
- chapters*
  - (definition of each chapter)
    - title*
    - description*
    - url*
    - time-required*
    - learning-goal*
    - learning-objectives*
      - (definition for each learning-objective)
        - learning-objective*
        - competency*
        - data-flow*
        - blooms-category*
        - assessment
        - jupyter-book-glue-id (only for internal use)
    - supplemented-by
      - (definition for each supplemental material)
        - title*
        - url*
        - note
    - language (only allowed if it overwrites the books language)
- date-issued*
- date-modified*
- version*
- context-of-creation*
- quality-assurance*
- learning-resource-type*
- schema-version*
- license*
  - content*
  - code
```

### Diagrams

You can find an approximation of the QAP in the form of UML class diagrams <a
href="https://quadriga-dk.github.io/QUADRIGA-Application-Profile/diagrams/"
target="_blank">here</a>.

To rebuild the diagrams make sure [Docker](https://www.docker.com)
(recommended) or [PlantUML](https://plantuml.com) is installed and run `just
diagrams`.

## Usage

### Creating Metadata Files

Create a YAML file following the QAP structure. Start with the minimal example
in [`examples/minimal_metadata.yml`](./examples/minimal_metadata.yml).

You can use `latest` in the schema URL, but in production we recommend picking
a specific `qap-version` like `v1.0.0`.

### Vocabulary Mappings (x-mappings)

The QUADRIGA Application Profile uses a custom `x-mappings` extension field in
the JSON-Schema implementation to document how elements (classes, properties or
relations) map to select vocabularies and schema. This approach co-locates
crosswalk mappings directly within the definition of the QAP, making them
machine-readable and version-controlled alongside the QAP itself.

#### Structure

Each QAP element can include an `x-mappings` field that maps to seven target
vocabularies:

```json
{
  "title": {
    "type": "string",
    "description": "Titel des Buchs",
    "x-mappings": {
      "dc": {
        "relation": "skos:exactMatch",
        "target": "dc:title"
      },
      "dcat": null,
      "dcterms": {
        "relation": "skos:exactMatch",
        "target": "dcterms:title"
      },
      "hermes": {
        "relation": "skos:exactMatch",
        "target": "hermes:title"
      },
      "lrmi": null,
      "modalia": null,
      "schema": {
        "relation": "skos:exactMatch",
        "target": "schema:name"
      }
    }
  }
}
```

#### Target Vocabularies

- **dc**: [Dublin Core Elements](http://purl.org/dc/elements/1.1/)
- **dcat**: [Data Catalog Vocabulary](http://www.w3.org/ns/dcat#)
- **dcterms**: [DCMI Metadata Terms](http://purl.org/dc/terms/)
- **hermes**: [HERMES OER metadata schema](https://zenodo.org/records/17279619)
- **lrmi**: [Learning Resource Metadata Initiative](http://purl.org/dcx/lrmi-terms/)
- **modalia**: [Modalia ontology](https://purl.org/ontology/modalia#)
- **schema**: [Schema.org](http://schema.org/)

#### SKOS Relation Types

Mappings use [SKOS mapping
relations](https://www.w3.org/TR/skos-reference/#mapping) to indicate semantic
relationships:

- `skos:exactMatch`: Properties are semantically equivalent
- `skos:closeMatch`: Properties are closely related but not identical
- `skos:broadMatch`: Target property is broader in meaning
- `skos:narrowMatch`: Target property is narrower in meaning
- `skos:relatedMatch`: Properties are related but not hierarchically

Use `null` when no appropriate mapping was identified for a given vocabulary.

#### Mapping Matrix

An interactive mapping matrix showing all QAP elements mapped against the
target vocabularies is available for each schema version:

- **Latest:**
  [https://quadriga-dk.github.io/QUADRIGA-Application-Profile/latest/mapping-matrix.html](https://quadriga-dk.github.io/QUADRIGA-Application-Profile/latest/mapping-matrix.html)
- **v1.0.0:**
  [https://quadriga-dk.github.io/QUADRIGA-Application-Profile/v1.0.0/mapping-matrix.html](https://quadriga-dk.github.io/QUADRIGA-Application-Profile/v1.0.0/mapping-matrix.html)

The matrix is color-coded by SKOS relation type (using a colorblind-safe
palette), includes links to the schema elements and target vocabulary terms,
and shows mapping comments as tooltips.

To build the mapping matrix locally, run `just mapping-matrix` (output will be
in `_build/<version>/mapping-matrix.html`).

#### Meta-Schema

The `x-mappings` structure is validated by
[x-mappings-meta-schema.json](./x-mappings-meta-schema.json), which ensures
consistent mapping documentation across all schema files.

## Documentation

- **HTML Documentation:**
  [https://quadriga-dk.github.io/QUADRIGA-Application-Profile/](https://quadriga-dk.github.io/QUADRIGA-Application-Profile/)
- **Latest Schema:**
  [https://quadriga-dk.github.io/QUADRIGA-Application-Profile/latest/schema.json](https://quadriga-dk.github.io/QUADRIGA-Application-Profile/latest/schema.json)

To build the HTML documentation locally, run `just html` (output will be in
`_build/`).

### Local Development

This project uses [just](https://just.systems) as a command runner. Install it
with `brew install just` (macOS) or see the [installation
docs](https://just.systems/man/en/packages.html) for other platforms. Run `just
--list` to see all available recipes:

```
just validate           # Validate x-mappings in all schema files
just diagrams           # Build all PlantUML diagrams (auto-detect Docker vs local)
just diagrams docker    # Force Docker for building diagrams
just diagrams list      # List available diagrams
just diagram <name>     # Build a single diagram by name
just html               # Build HTML documentation (validates first)
just mapping-matrix     # Generate mapping matrix HTML for all versions
just build              # Build everything: diagrams + HTML docs + mapping matrix
just serve              # Serve built HTML at http://localhost:8000
just clean              # Clean build artifacts
```
