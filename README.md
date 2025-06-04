# Dash Dashboard

This `dash_dashboard` submodule is a component of the Sagittarius project's visualization suite. It leverages the [Plotly Dash](https://dash.plotly.com/) framework, built on [Plotly.js](https://plotly.com/javascript/) and React.js, to create interactive web-based dashboards for visualizing data sourced from FIWARE entities.

## Table of Contents

- [Overview](#overview)
- [Key Features](#key-features)
- [Getting Started](#getting-started)
- [Configuration](#configuration)
- [Usage](#usage)
- [Making Changes](#making-changes)
- [Troubleshooting](#troubleshooting)
- [Docs](#docs)

## Overview

This dashboard is designed to consume the JSON output from the Sagittarius compiler (specifically the [`Dash`](../compiler/sagc/src/dash.rs) struct) and render visualizations. It dynamically creates plots based on the configuration, including panel types like `GeoMap`, `PieChart`, `XYChart`, etc.

## Key Features

- Dynamic rendering of visualizations based on compiler output.
- Interactive charts and graphs for various metrics.
- Support for different panel types as defined in the Sagittarius configuration language.
- Integration with FIWARE data sources.

## Getting Started

1.  **Build the Docker Image:**
    Navigate to the `src/dash_dashboard/` directory in your terminal and run:

    ```bash
    docker build -t local/dash_dashboard:latest .
    ```

    This command builds a Docker image using the included [Dockerfile](./Dockerfile).

2.  **Run the Container:**
    You can run the container as part of the main compose file [docker-compose.yaml](../../docker-compose.yaml).

## Configuration

The dashboard is primarily configured by the JSON output from the Sagittarius compiler. This JSON file

**Compiler Output (`config.json`):** This file dictates the service details, data sources, application layout, and visualizations (panels) to be rendered. It's derived from the Sagittarius configuration language.

An example of the output [`config.json`](./config.json) can be found here locally.

It is important to note that the way the compilation works, this config file is uploaded to our own Azure `sagstorage` blob webstorage and, it gets fetched from there when building the container of the dashboard. Complication may arise with this fetching process you should be aware of, e.g. authentication issue, wrong url, etc.

## Usage

Once the dashboard is running with a valid `config.json` (compiler output), navigate to `http://localhost:8050`. The dashboard will display visualizations as defined in the `application.visualizations` section of the configuration. Interactions like filtering or drill-downs depend on the specific panel types and their implementations (e.g., selectors handled in [`src/dash_dashboard/src/config.py`](src/dash_dashboard/src/config.py)).

## Making Changes

This is probably one of the hardest modules to add new features to as it takes close collaboration with other modules. You would most likely need to create new branches for `dash_dashboard`, `compiler`, `fiware_admin`. Generally these are the main steps:

1. Decide on the new feature you want to add.
2. Research datasets online that you could use to develop this use case. Here are a few common sources for Austrian datasets:
    - https://www.data.gv.at/
    - https://data.europa.eu/en
3. Once you have the dataset, you should put it into the `examples` directory of `fiware_admin`.
    - You should also add a short README describing the dataset and denoting the source.
    - Then process it to be compatible with the Fiware NGSI v2 format.
4. Once the data is well formatted, you should change [fiware_admin.Dockerfile](../../fiware_admin.Dockerfile) to upload your dataset into the Fiware Orion service.
5. Now based on what component you are expanding you have to update the actual Plotly visualization logic in [visualizations.py](./src/visualizations.py) and accordingly update the component definitions in the compiler if needed, usually found in [dash.rs](../compiler/sagc/src/dash.rs) and [sections.rs](../compiler/sagc/src/sections.rs).

>[!NOTE]
> Whenever you make changes in this component, you have to manually rebuild the image as seen in [Getting Started](#getting-started). You do not have to stop any of the other containers, they are completely independent and can continue running.

## Troubleshooting

- **Dashboard not loading / No link returned:**
  - Ensure Docker container is running and the `config.json` is accessible from the Azure storage.
  - As of now, the frontend shows a success message, because the compilation did go through, it is the dash image that is failing. Check the container's logs.
- **Data not appearing:**
  - Ensure the data sources specified in `config.json` are accessible and provide data.
  - Check for errors in the browser's developer console and the Fiware Admin container logs to see whether your data has really been uploaded.
- **Dashboard Compiles Once and no More:**
  - Make sure to try and delete the container before compiling again, inspect logs of Dash container on second compilation.

## Docs

- **Plotly Python Open Source Graphing Library:** [https://plotly.com/python/](https://plotly.com/python/)
- **Plotly Dash User Guide & Documentation Python:** [https://dash.plotly.com/](https://dash.plotly.com/)
