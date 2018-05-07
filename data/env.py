import os
import sys
import yaml

DATA_DIR = os.path.dirname(__file__)

# App-level metadata.
META = yaml.safe_load(open(os.path.join(DATA_DIR, "../meta.yml")))
DOMAINS = os.environ.get("DOMAINS", META["data"]["domains_url"])

# domain-scan paths (MUST be set in env)
SCAN_COMMAND = os.environ.get("DOMAIN_SCAN_PATH", None)
GATHER_COMMAND = os.environ.get("DOMAIN_GATHER_PATH", None)


# post-processing and uploading information
PARENTS_DATA = os.path.join(DATA_DIR, "./output/parents")
PARENTS_RESULTS = os.path.join(DATA_DIR, "./output/parents/results")
SUBDOMAIN_DATA = os.path.join(DATA_DIR, "./output/subdomains")
SUBDOMAIN_DATA_GATHERED = os.path.join(DATA_DIR, "./output/subdomains/gather")
SUBDOMAIN_DATA_SCANNED = os.path.join(DATA_DIR, "./output/subdomains/scan")

DB_DATA = os.path.join(DATA_DIR, "./db.json")
BUCKET_NAME = META["bucket"]
AWS_REGION = META["aws_region"]

# DAP source data
ANALYTICS_URL = META["data"]["analytics_url"]

# a11y source data
A11Y_CONFIG = META["a11y"]["config"]
A11Y_REDIRECTS = META["a11y"]["redirects"]

### Parent domain scanning information
#
scanner_string = os.environ.get("SCANNERS", "pshtt,sslyze,analytics")
SCANNERS = scanner_string.split(",")

GATHER_SUFFIXES = os.environ.get("GATHER_SUFFIXES", ".ca,.gov.ca")

# names and options must be in corresponding order
GATHERER_NAMES = ["other", "canada-gov"]

GATHERER_OPTIONS = [
    "--other=%s" % META["data"]["other_subdomains_url"], "--canada-gov=%s" % DOMAINS
]

# Run these scanners over *all* (which is a lot) discovered subdomains.
SUBDOMAIN_SCANNERS = ["pshtt", "sslyze"]

# Used if --lambda is enabled during the scan.
LAMBDA_WORKERS = 900

# Quick and dirty CLI options parser.
def options():
    options = {}
    for arg in sys.argv[1:]:
        if arg.startswith("--"):

            if "=" in arg:
                key, value = arg.split("=")
            else:
                key, value = arg, "true"

            key = key.split("--")[1]
            key = key.lower()
            value = value.lower()

            if value == "true":
                value = True
            elif value == "false":
                value = False
            options[key] = value

    return options
