CircleCI Status: [![CircleCI](https://circleci.com/gh/cds-snc/pulse.svg?style=svg)](https://circleci.com/gh/cds-snc/pulse)

## Track Government of Canada domains's adherance to digital security practices

How the GC domain space is doing at best practices and federal requirements.

| Documentation                                           |
| ------------------------------------------------------- |
| [Development Setup Instructions](#development-setup)    |
| [Local Deploy Step-by-step](docs/local-instructions.md) |
| [Deployment Docs](docs/deploy.md)                       |

## Development Setup

For development purposes it is recommended that you install [mongodb](https://www.mongodb.com/) and run the database locally.

This dashboard is a [Flask](http://flask.pocoo.org/) app written for **Python 3.5 and up**. We recommend [pyenv](https://github.com/yyuu/pyenv) for easy Python version management.

To setup local python dependencies you can run `make setup` from the root of the repository. We recommend that this is done from within a virtual environment

### Web app

From the `track_digital` subdirectory

* Install dependencies:

```bash
pip install -r requirements.txt
```

* If developing this dashboard app, you will also need the development requirements
```bash
pip install .[development]
```

* If developing the stylesheets, you will also need [Sass](http://sass-lang.com/), [Bourbon](http://bourbon.io/), [Neat](http://neat.bourbon.io/), and [Bitters](http://bitters.bourbon.io/).

```bash
gem install sass bourbon neat bitters
```

* If editing styles during development, keep the Sass auto-compiling with:

```bash
make watch
```

* And to run the app in development, use:

```bash
make debug
```

This will run the app with `DEBUG` mode on, showing full error messages in-browser when they occur.

When running in development mode it is expected that you have a database running locally, accessable via `localhost:27017`.

To produce some data for the flask app to display, follow the instructions in the following section.

### Domain scanner

from the `tracker` subdirectory

* Install dependencies:

```bash
pip install -r requirements.txt
```

* If developing tracker, you will also need the development requirements
```bash
pip install .[development]
```

#### Install domain-scan and dependencies

Download and set up `domain-scan` [from GitHub](https://github.com/cds-snc/domain-scan) as per it's setup instructions.

`domain-scan` in turn requires [`pshtt`](https://github.com/dhs-ncats/pshtt) and [`sslyze`](https://github.com/nabla-c0d3/sslyze). These can be installed directly via `pip`.

The app requires you to set one environment variable:

* `DOMAIN_SCAN_PATH`: A path to `domain-scan`'s `scan` binary.
* `DOMAIN_GATHER_PATH`: A path to `domain-scan`'s `gather` binary.

However, if you don't have `pshtt` and `sslyze` on your PATH, then `domain-scan` may need you to set a couple others:

* `PSHTT_PATH`: Path to the `pshtt` binary.
* `SSLYZE_PATH`: Path to the `sslyze` binary.

#### Then run it

From the `tracker` subdirectory:

```
tracker run --scan here
```

This will kick off the `domain-scan` scanning process for HTTP/HTTPS and DAP participation, using the domain lists as specified in `tracker/data/data_meta.yml` for the base set of domains to scan.

Then it will run the scan data through post-processing producing some JSON and CSV files as scan artifacts and finally uploading the results into the database that the frontend uses to render the information (by default if not further specified `localhost:21017/tracker`).

For a more detailed step by step procedue of getting a local development deployment going, checkout out the [Local Deploy Step-by-step](docs/local-instructions.md) document!

#### Scanner CLI

The scanner portion has a CLI that can be used to perform individual parts of the scanning in isolation of the other steps.
By following the steps to setup the Scanning portion, this CLI should be readily accessable to you (if you have activated the environment you installed it into).
As you may have guesed from the command in the previous section, the CLI command is `tracker`.

Help on how to use the CLI can be output via the command `tracker --help`


## Public domain

This project is in the worldwide [public domain](LICENSE.md). As stated in [CONTRIBUTING](CONTRIBUTING.md):

> This project is in the public domain within the United States, and copyright and related rights in the work worldwide are waived through the [CC0 1.0 Universal public domain dedication](https://creativecommons.org/publicdomain/zero/1.0/).
>
> All contributions to this project will be released under the CC0 dedication. By submitting a pull request, you are agreeing to comply with this waiver of copyright interest.

### Origin 

This project was originally forked from [18F](https://github.com/18f/pulse) and has been modified to fit the Canadian context.
