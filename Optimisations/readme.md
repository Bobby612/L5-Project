# Optimisations
Take a RVSDG program expressed as a BigraphER txt representation and apply optimisations.

Author: Borislav Kratchanov, b.k.kratchanov@gmail.com

Copying: Check License file in top level of GitHub repository for information on redistribution and use

## Use
1. Concatenate the model files
2. Run the model with the program txt as the initial state

*Example:*

`cat controls.big optimisation_rules.big begin.big > optimisation.big`

`bigrapher full -t transition/transition -s -f svg,txt -i program.txt optimisation.big`

## Implemented Optimisations
* Common Node Elimination
* Node Push-out -- for Gamma and Theta Nodes
* Node Pull-in
* Invariant Value Redirection
