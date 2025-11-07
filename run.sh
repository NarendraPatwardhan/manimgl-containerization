#!/bin/bash

bash -c "xvfb-run -s '-screen 0 1920x1080x24' manimgl main.py PrimaryScene -qmw"
