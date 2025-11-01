#!/bin/bash

# Install script for SEAD Authority Service database

/home/roger/bin/sql -q -t -A -f sql/00_install_all.sql
