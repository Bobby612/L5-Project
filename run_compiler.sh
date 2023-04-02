#!/bin/bash

# # # # # # # # # # # # # # # # 
# Author: Borislav Kratchanov
# Copyright: 
# # # # # # # # # # # # # # # # 


SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
WORK_DIR=$(pwd)
steps=0
opt_sim=0

print_usage() {
    printf "Usage: 
    run_compiler {mode} {file}

    Modes:
    -c Output RVSDG with CFG for function body
    -r Output RVSDG
    -o Output Optimised RVSDG
    -os Output Optimised RVSDG using only one optimisation trace

    Input File:
    A valid LLVM IR file in assembly format

    Output:
    A folder with all of the generated files and states

"
}

case "$1" in
    "-c")
    echo "Output RVSDG with CFG for function body"
    steps=1
    ;;

    "-r")
    echo "Output RVSDG"
    steps=2
    ;;

    "-o")
    echo "Output Optimised RVSDG"
    steps=3
    ;;

    "-os")
    echo "Output Optimised RVSDG (simulated)"
    steps=3
    opt_sim=1
    ;;

    *)
    print_usage
    ;;
esac

if [ $steps -eq 0 ] 
then
    exit
fi

if [ ! $2 ]
then
    exit
fi

OUTPUT_NAME="${2%.ll}"
OUTPUT_DIR="$WORK_DIR/${OUTPUT_NAME}_$(date +"%F-%H%M%S")"
start=`date +%s`

mkdir "$OUTPUT_DIR"
echo "Save Output in $OUTPUT_DIR"
cp "$2" "$OUTPUT_DIR/$2"

cd "$OUTPUT_DIR"

echo "Converting LLVM IR to RVSDG with CFG"

STATUS=` python "$SCRIPT_DIR/LLtoBig3/llvm_to_bigrapher.py" "$2" `

echo "$STATUS"

if [ $STATUS != "ok" ]
then
    exit
fi

if [ $steps -gt 1 ]
then
    echo "Converting CFG to Gamma and Theta Nodes"
    cat "$SCRIPT_DIR/BigCFGtoRVSDG/controls.big" "$SCRIPT_DIR/BigCFGtoRVSDG/rewrite_rules.big" "$SCRIPT_DIR/BigCFGtoRVSDG/cfgbig.big" "$OUTPUT_NAME.big"  "$SCRIPT_DIR/BigCFGtoRVSDG/semicolon.big" "$SCRIPT_DIR/BigCFGtoRVSDG/begin.big" > control_flow_bigraph_full_model.big
    mkdir cfg_to_rvsdg
    bigrapher sim -t cfg_to_rvsdg/transition -s -f txt,svg control_flow_bigraph_full_model.big
    lambdain=`grep -o "Lambda" "$OUTPUT_NAME.big" | wc -l`
    lambdaout=`grep -o "rg_lone" "cfg_to_rvsdg/transition.svg" | wc -l`

    if [ $lambdain -eq $lambdaout ]
    then
        cat `ls -v -r ./cfg_to_rvsdg/*.txt | head -2 | tail -1` > "./${OUTPUT_NAME}.txt"
        echo "Succes"
    else 
        echo "Fail: Converted $lambdaout Lambda regions out of $lambdain"
        exit
    fi

fi

if [ $steps -gt 2 ]
then 
    echo "Optimising RVSDG"
    mkdir rvsdg_opt

    if [ $opt_sim -eq 1 ]
    then
        bigrapher sim -t rvsdg_opt/transition -s -f svg,txt -i "./${OUTPUT_NAME}.txt" "$SCRIPT_DIR/Optimisations/optimisation.big"
    else
        bigrapher full -t rvsdg_opt/transition -s -f svg,txt -i "./${OUTPUT_NAME}.txt" "$SCRIPT_DIR/Optimisations/optimisation.big"
    fi

fi

end=`date +%s`
runtime=$((end-start))
echo "Done in ${runtime}s"

    


