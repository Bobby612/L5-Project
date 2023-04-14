# BigraphER RVSDG Intra-procedural Analysis
Turn the CFG in each Lambda Node Region into a valid RVSDG Region with Gamma and Theta nodes.

Author: Borislav Kratchanov, b.k.kratchanov@gmail.com

Copying: Check License file in top level of GitHub repository for information on redistribution and use

## Use
1. Paste the input graph in the directory as {name}.big
2. Concatenate the files in the directory
3. Run a simulation on the concatenated file
4. Check the simulation trace to make sure all functions are completely transformed
    - There need to be as many applications of the rule rg_lone_region_* as there are functions
5. The last state output is the RVSDG

*Example:*   
`cat controls.big rewrite_rules.big cfgbig.big {name}.big  semicolon.big begin.big > control_flow_bigraph.big`

`bigrapher sim -S 5000 -t ./transition/transition -s -f txt,svg control_flow_bigraph.big`

## Known limitations
* Does not support irreducible control flow
* Not all controls are needed in controls.big

## Files
### begin.big
The rule priorities

### controls.big
The definition of the controls used in the model

**NB:** Some of them are no longer required

### rewrite_rules.big
The bigraph reaction rules

### cfgbig.big, semicolon.big
Syntax to make the concatenated BigraphER model valid