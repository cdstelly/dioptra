# Dioptra

The project documentation is in the `docs` folder and compiled using Sphinx.
To build the documentation locally, make sure you have Docker installed and try to pull the builder images:

    make pull-latest-ci

If you do not have access to the project's Docker registry, then you can build and tag them manually:

    make build-ci tag-latest-ci

The documentation can then be built with,

    make docs

When the build is done, open `docs/build/index.html` in your web browser.
