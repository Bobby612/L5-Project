# LLVM to Bigrapher
Take an LLVM program and perform inter-procedural analysis and partially intra-procedural analysis. Output an inter-procedural RVSDG with Omega, Lambda and Delta nodes, with CFG as Lambda node Regions. Each CFG block has an RVSDG Region segment with simple nodes. 

## Use
Pass the name of a valid {filename}.ll LLVM assembly file as a command line argument to llvm_to_bigrapher.py. It will convert it and save {filename}.big -- the graph corresponding to the file, and {filename}.json -- the text arguments that should have been included in the graph (they are removed because of partial support for strings in BigraphER).

*Example:* `python llvm_to_bigrapher.py example.ll`

**NB:** If the file contains an unsupported instruction, its opcode will be printed to stdout and the instruction will be ignored.

## Requirements
* Python 3.10
* llvmlite 0.39.1
* LLVM 11

## Known issues
* The way types are recorded is sub-optimal -- would be good to split type and dependency order.
    * Currently, dependency order is first, type is second
* Alignment is not recorded at many places
* Do something more reasonable with unsupported instructions. Currently, they are just printed out and ignored.

## Files
### LLVM to Bigrapher
The main file

### Parse Structure
File containing the functions emitting the different LLVM structures -- global variables, functions, blocks, instructions

### Parse Instructions
Each method takes an instruction and any additional needed arguments (like state).
It returns a dictionary with its information and the links that need to be closed for the instruction at the region level, plus any additional information if needed.

The fields of the dictionary are:
* opcode -- string
* write -- list
* read -- list
* type -- list
* options -- list
* in_instruction -- list of the internal links to the instruction that need to be closed

#### Supported Instructions
call; sext; getelementptr; alloca; bitcast; sitofp; ret; icmp; br; load; store; add; sub; mul; shl; srem; urem; sdiv; fadd; fsub; fmul; fdiv; frem

### Utils
Miscellaneous utilities

### Global Variables
The global variables for the project, in a separate file to avoid circular imports