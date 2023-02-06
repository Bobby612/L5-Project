#!/bin/bash
in_cfg=false
out_ct=false
out_rvsdg=false
output_format="svg"
input_file=""
output_file=""

while getopts I:C:R:c:r:o:f:F flag
do
    case "${flag}" in
        I) input_file=${OPTARG}; in_cfg=true ;; ## Input CFG
        C) input_file=${OPTARG} ;; ## Input Control tree
        R) input_file=${OPTARG} ;; ## Input RVSDG

        c) output_file=${OPTARG}; out_ct=true ;; ## Output control tree
        r) output_file=${OPTARG}; out_rvsdg=true ;; ## Output RVSDG
        o) output_file=${OPTARG}; ;; ## Output optimised RVSDG

        f) output_format=${OPTARG} ;; ## Output format
        F) ;; ## Input format
    esac
done

if $in_cfg && $out_ct
then
    cat "controls.big" "ct_rules.big" "cfgbig.big" "${input_file}" "semicolon.big" "ct_begin.big" > temp
    bigrapher sim -t "${output_file}" -s -f "${output_format}" temp
fi

if $in_cfg && $out_rvsdg
then
    cat "controls.big" "ct_rules.big" "cfgbig.big" "${input_file}" "semicolon.big" "ct_begin.big" > temp
    bigrapher sim -s . -f txt temp

    last_state=0
    for f in ./*.txt
    do
        current_state="${f//[^0-9]/}"
        if [ current_state > last_state ]
        then
            last_state=${current_state}
        fi
    done
    cat "${last_state}.txt" > temp_init
    rm *.txt

    cat "controls.big" "rvsdg_rules.big" "rvsdg_begin.big" > temp
    bigrapher sim -t "${output_file}" -s -f "${output_format}" -i temp_init temp
    
    

fi



