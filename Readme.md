# Optimising Compiler implemented using declarative bigraph reaction rules
`L5 Project`

Author: Borislav Kratchanov, b.k.kratchanov@gmail.com

Copying: Check License file in top level of GitHub repository for information on redistribution and use

## NB: Most up-to-date information on the implementation can be found on github, at https://github.com/Bobby612/L5-Project/tree/develop
If you have any questions regarding the implementation, do not hesitate to contact me at b.k.kratchanov@gmail.com 

## Implementation Status
The compiler converts an LLVM textual IR to RVSDG expressed as a bigraph and applies optimisations to the IR.

### Implementation Limitations:
* No support for mutual recursion
* No support for irreducible control flow
* No conversion back to LLVM IR from the optimised bigraph RVSDG


## Dependencies
* Python 3.10
* llvmlite python package (v0.39.1 used)
* LLVM 11 (for llvm lite and for compiling .c to .ll files)
* bigrapher (v1.9.3 used)

## Use
* Using the `run_compiler.sh` script in the top-level folder:
`./run_compiler -{option} {file}.ll`

The options available are:
* -c    Output Inter-procedural RVSDG with CFG for function bodies (only Python stage) as {file}.big
    * Also outputs {file}.json, which includes all of the string parameters used in the .big file
* -r    Output full RVSDG as {file}.txt, together with its BRS simulation trace and the output from above stages
* -o    Output full optimisation BRS (and output from above stages)
* -os   Output a simulated trace of the optimisation BRS

The last two options differ only in the number of states that need to be explored and have the same general format.

## Folder structure

### Automating Pipeline (abandoned)
Contanis attempts to automate the pipeline, but has been abandoned for now.

### BigCFGtoRVSDG
Contains the bigraph models to perform Intra-procedural Translation

### Contrived LLVM or C Examples
Contains instances used for testing during development

### Count Identifiers
Contains a python script counting identifiers, keywords and lines of code of a C or BigraphER program according to very simple rules.    
NB: input programs should not contain strings or comments

### jlm_xlm_decipher
Take an RVSDG output from jlm (https://github.com/phate/jlm) in xml format and print its Nodes

### LLtoBig3
Program to perform RVSDG Inter-procedural translation to LLVM IR file and output it as a bigraph

### Optimisations
Contains the bigraph models to perform optimisations on the bigraph RVSDG


