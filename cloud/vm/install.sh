#!/bin/bash

# Single argument - PROJECT_ID (e.g. "my-gcp-project-develop")
PROJECT_ID=$1

# NOTE: LC_CTYPE must be removed otherwise installation will fail; it gets confused when building R
# LC_CTYPE defines how characters are converted (language specific)
export LC_CTYPE=

echo
echo "*** INFO Creating 'runner' user"
echo
sudo adduser --disabled-password --gecos "" runner

echo
echo "*** INFO Updating and upgrading apt-get"
echo
# From https://manpages.debian.org/unstable/apt/apt-get.8.en.html - see "--allow-releaseinfo-change"
# Required as "buster" version of Debian has moved status to "oldstable":
#
# N: Repository 'http://security.debian.org/debian-security buster/updates InRelease' changed its 'Suite' value from 'stable' to 'oldstable'
# N: Repository 'http://deb.debian.org/debian buster InRelease' changed its 'Version' value from '10.5' to '10.11'
# N: Repository 'http://deb.debian.org/debian buster InRelease' changed its 'Suite' value from 'stable' to 'oldstable'
# N: Repository 'http://deb.debian.org/debian buster-updates InRelease' changed its 'Suite' value from 'stable-updates' to 'oldstable-updates'
#
# Rather than re-validate R rjdemetra and related dependencies, staying with old copy of Debian at VM construction.

sudo apt-get --allow-releaseinfo-change update
sudo apt-get -y upgrade

echo
echo "*** INFO Installing R"
echo
# R (seems to be R 3.5.2)
sudo apt-get install -y -qq r-base

echo
echo "*** INFO Installing base xml2 for R xml2 lib (and devtools)"
echo
sudo apt-get install -y -qq libxml2-dev

echo
echo "*** INFO Installing fontconfig1 and cairo2 for ggPlot in R"
echo
sudo apt-get install -y -qq libfontconfig1-dev
sudo apt-get install -y -qq libcairo2-dev

echo
echo "*** INFO Installing R devtools (for R github package support)"
echo
#sudo R -e 'install.packages("devtools", dependencies=TRUE)'
sudo apt-get -y -qq install r-cran-devtools

echo
echo "*** INFO Installing R xts library"
echo
#sudo R -e 'install.packages("xts", dependencies=TRUE)'
sudo apt-get -y -qq install r-cran-xts

echo
echo "*** INFO Installing R dplyr library"
echo
# data wrangling
#sudo R -e 'install.packages("dplyr", dependencies=TRUE)'
sudo apt-get -y -qq install r-cran-dplyr

echo
echo "*** INFO Installing R tidyr library"
echo
# data wrangling
# r-cran-tidyr is 0.8.2 - too old
#sudo apt-get -y -qq install r-cran-tidyr
sudo R -e 'install.packages("tidyr", dependencies=TRUE)'

echo
echo "*** INFO Installing R lubridate library"
echo
# date manipulation
sudo apt-get -y -qq install r-cran-lubridate

echo
echo "*** INFO Installing base OpenSSL library and installing R imputeTS via R package"
echo
# missing data imputation
# Needed for RCurl, used by ggtext
#sudo apt-get -y -qq install aptitude
sudo apt-get -y -qq install libcurl4-openssl-dev
sudo R -e 'install.packages("imputeTS", dependencies=TRUE)'

echo
echo "*** INFO Installing base Sodium library and installing R bigrquery via R package"
echo
# Big Query access
sudo apt-get -y -qq install libsodium-dev
sudo R -e 'install.packages("bigrquery", dependencies = TRUE)'

echo
echo "*** INFO Installing ggExtra R package to create tidier graphs"
echo
sudo R -e 'install.packages("ggExtra", dependencies = TRUE)'


echo
echo "*** INFO Installing data.table R package to simplify list access"
echo
sudo apt-get -y -qq install r-cran-data.table

echo
echo "*** INFO Installing R Java support package"
echo
sudo apt-get -y -qq install r-cran-rjava

echo
echo "*** INFO Installing R SEATS package from GitHub"
echo
sudo R -e 'library(devtools);install_github("palatej/rjdhighfreq")'

echo
echo "*** INFO Installing R hms and testthat libraries for test support"
echo
sudo apt-get -y -qq install r-cran-hms
sudo apt-get -y -qq install r-cran-testthat

echo
echo "*** INFO Installing R viridis library (graph support)"
echo
# This will also pull in ggplot2 for R
sudo apt-get -y -qq install r-cran-viridis

echo
echo "*** INFO Installing R stringr library (string formatting support)"
echo
sudo apt-get -y -qq install r-cran-stringr

echo
echo "*** INFO Copying code over to 'runner' user from installation user"
echo
sudo cp runner-startup.sh ~runner

sudo cp bigquery-r-auth-token.json ~runner
sudo cp *.R ~runner

sudo cp backfill-ne-auth-token.json ~runner
sudo cp -r chrono_lens ~runner
sudo cp -r dsc_lib ~runner
sudo cp *.py ~runner
sudo cp NEtraveldata_cctv.json ~runner

sudo mkdir ~runner/logs
sudo mkdir ~runner/cache
sudo mkdir ~runner/outputs

sudo chown -R runner ~runner/*
sudo chgrp -R runner ~runner/*
sudo sed -i "s/PROJECT_ID_PLACEHOLDER/${PROJECT_ID}/" ~runner/runner-startup.sh
sudo sed -i "s/PROJECT_ID_PLACEHOLDER/${PROJECT_ID}/" ~runner/data_impute_and_seats_run.R
sudo sed -i "s/PROJECT_ID_PLACEHOLDER/${PROJECT_ID}/" ~runner/data_impute_and_seats_functions.R


echo
echo "*** INFO installing Python dependencies"
echo
sudo apt-get -y -qq install python3-pip
sudo python3 -m pip install -U pip
sudo pip3 install -r requirements-gcloud.txt

# check six version; reports:
# google-api-core 1.23.0 has requirement six>=1.13.0, but you'll have six 1.12.0 which is incompatible.
sudo pip3 install six==1.13


echo
echo "*** INFO Installing GCP memory logging"
echo
# https://cloud.google.com/monitoring/agent/installation#joint-install
curl -sSO https://dl.google.com/cloudagents/add-monitoring-agent-repo.sh
sudo bash add-monitoring-agent-repo.sh
# Update needed to reflect availability of monitoring agent
sudo apt-get update
sudo apt-get -y -qq install stackdriver-agent
sudo service stackdriver-agent start
echo
echo "Memory service agent status (should be 'OK'):"
sudo grep collectd /var/log/{syslog,messages} | tail
