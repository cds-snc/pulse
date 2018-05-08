#!/bin/bash

# Set the path to domain-scan.
export DOMAIN_SCAN_PATH=/opt/scan/domain-scan/scan
export DOMAIN_GATHER_PATH=/opt/scan/domain-scan/gather

# Baseline where Pulse is checked out to
export PULSE_HOME=/opt/scan/pulse

# Make sure that AWS credentials have been configured
mkdir -p ~/.aws
cat > ~/.aws/credentials << EOF
[lambda]
aws_access_key_id=$PULSE_AWS_KEY_ID
aws_secret_access_key=$PULSE_AWS_SECRET
EOF 

cat > ~/.aws/config << EOF
[profile lambda]
region=$PULSE_AWS_REGION
output=json
EOF

cd $PULSE_HOME
. .env/bin/activate
export
ls -a
pulse run --scan here 
