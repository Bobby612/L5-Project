#!/bin/bash



if [ -z "$1" ]
then
    for file in *.ll
    do 
        python llvm_to_bigrapher.py "$file"
    done
    for file in *.big
    do
        echo $file
        cat "$file" > ../BigCFGtoRVSDG/cfg.big
        cd ../BigCFGtoRVSDG/
        cat controls.big rewrite_rules.big cfgbig.big cfg.big  semicolon.big begin.big > control_flow_bigraph.big
        bigrapher sim -t .transition/transition -s -f txt control_flow_bigraph.big
        cat `ls -v -r ./.transition/*.txt | head -2 | tail -1` > "../Optimisations/${file%.big}.txt"
        rm ./.transition/*.txt
        cd ../LLtoBig3
    done
else
    file=$1
    echo $file
    python llvm_to_bigrapher.py "$file"
    file="${file%.ll}.big"
    cat "$file" > ../BigCFGtoRVSDG/cfg.big
    cd ../BigCFGtoRVSDG/
    cat controls.big rewrite_rules.big cfgbig.big cfg.big  semicolon.big begin.big > control_flow_bigraph.big
    bigrapher sim -S 5000 -t .transition/transition -s -f txt,svg control_flow_bigraph.big 
    # bigrapher validate -d . -f txt,svg control_flow_bigraph.big 
    cat `ls -v -r ./.transition/*.txt | head -2 | tail -1` > "../Optimisations/${file%.big}.txt"
    rm ./.transition/*.txt
    cd ../LLtoBig3
fi