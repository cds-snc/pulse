[![Code Climate](https://codeclimate.com/github/18F/pulse/badges/gpa.svg)](https://codeclimate.com/github/18F/pulse) [![Dependency Status](https://gemnasium.com/badges/github.com/18F/pulse.svg)](https://gemnasium.com/github.com/18F/pulse)
[![CircleCI](https://circleci.com/gh/cds-snc/pulse.svg?style=svg)](https://circleci.com/gh/cds-snc/pulse)

## The pulse of the federal .gov webspace

How the .gov domain space is doing at best practices and federal requirements.

| Documentation  |  Other Links |
|---|---|
| [Setup and Deploy Instructions](#setup) |  [System Security Plan](https://github.com/18F/pulse/blob/master/system-security-plan.yml) |
| [a11y scan process](https://github.com/18F/pulse/blob/master/docs/a11y-instructions.md)  | [Ideas for new sections to add to the site](https://github.com/18F/pulse/blob/master/docs/other-sections.md) |
| [Ongoing Work](https://github.com/18F/pulse/blob/master/docs/project-outline.md) | [Backlog of feature requests and ideas](https://github.com/18F/pulse/issues?utf8=%E2%9C%93&q=is%3Aissue%20label%3Abacklog)  |
|  [ATO artifacts](https://github.com/18F/pulse/blob/master/docs/ato.md)  | [Open Source Reuse of the site](https://github.com/18F/pulse/blob/master/docs/reuse.md) |
| [Project Information](https://github.com/18F/pulse/blob/master/.about.yml)  |  |

## Setup

Pulse is a [Flask](http://flask.pocoo.org/) app written for **Python 3.5 and up**. We recommend [pyenv](https://github.com/yyuu/pyenv) for easy Python version management.

* Install dependencies:

```bash
pip install -r requirements.txt
```

* Install the data processing package
```bash
pip install .
```

* If developing Pulse, you will also need the development requirements
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

### Initializing dataset

To initialize the dataset with the last production scan data and database, there's a convenience function:

```
make data_init
```

This will download (using `curl`) the current live production database and scan data to the local `data/` directory.


### Install domain-scan and dependencies

Download and set up `domain-scan` [from GitHub](https://github.com/18F/domain-scan).

`domain-scan` in turn requires [`pshtt`](https://github.com/dhs-ncats/pshtt) and [`sslyze`](https://github.com/nabla-c0d3/sslyze). These can be installed directly via `pip`.

Pulse requires you to set one environment variable:

* `DOMAIN_SCAN_PATH`: A path to `domain-scan`'s `scan` binary.

However, if you don't have `pshtt` and `sslyze` on your PATH, then `domain-scan` may need you to set a couple others:

* `PSHTT_PATH`: Path to the `pshtt` binary.
* `SSLYZE_PATH`: Path to the `sslyze` binary.

### Configure the AWS CLI

To publish the resulting data to the production S3 bucket, install the official AWS CLI:

```
pip install awscli
```

And link it to AWS credentials that allow authorized write access to the `pulse.cio.gov` S3 bucket.

### Then run it

From the Pulse root directory:

```
pulse run
```

This will kick off the `domain-scan` scanning process for HTTP/HTTPS and DAP participation, using the `.gov` domain list as specified in `meta.yml` for the base set of domains to scan.

Then it will run the scan data through post-processing to produce some JSON and CSV files the Pulse front-end uses to render data.

Finally, this data will be uploaded to the production S3 bucket.


### Public domain

This project is in the worldwide [public domain](LICENSE.md). As stated in [CONTRIBUTING](CONTRIBUTING.md):

> This project is in the public domain within the United States, and copyright and related rights in the work worldwide are waived through the [CC0 1.0 Universal public domain dedication](https://creativecommons.org/publicdomain/zero/1.0/).
>
> All contributions to this project will be released under the CC0 dedication. By submitting a pull request, you are agreeing to comply with this waiver of copyright interest.
