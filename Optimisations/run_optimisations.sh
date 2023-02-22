#!/bin/bash

cat controls.big optimisation_rules.big begin.big > optimisation.big
bigrapher full -M 5000 -t .transition/transition -s -f svg,txt -i "$1" optimisation.big