import llvmlite.binding as llvm
from llvmlite.ir.instructions import *
from llvmlite.binding.value import ValueRef
import json
import sys, os

from parse_instructions import *
from parse_structures import *
from utils import *
import global_vars


"""

Author: Borislav Kratchanov
Copyright: 

Convert the LLVM structures of an LLVM program to RVSDG in BigraphER format.

"""


def main(file_name):
    llvm_assembly = ""
    with open(file_name, "r") as f:
        llvm_assembly = f.read()

    new_file_name = os.path.splitext(file_name)[0]

    llvm_module = llvm.parse_assembly(llvm_assembly)
    llvm_module.verify()

    import_functions = []
    global_function_nodes = []
    global_variable_nodes = []
    global_links = []
    data_types = []


    for global_variable in llvm_module.global_variables:
        gv, lk = parse_global_variable(global_variable)

        global_variable_nodes += [gv]
        global_links += [lk]
    
    for function in llvm_module.functions:
        fn, lk, import_function = parse_function(function)
        global_function_nodes += [fn]
        global_links += [lk]

        if import_function:
            import_functions += [import_function]
    
    data_types = list(map(transform_type3, list(enumerate(import_functions))))
    type_labels = list(map(lambda x : f" /olabel_{x}" ,list(range(0, len(data_types)))))

    import_functions_labels = list(map(create_label3, list(enumerate(import_functions))))
    import_labels = list(map(lambda x : "/" + x, import_functions + global_links))

    omega = \
f"""
{" ".join(import_labels + type_labels)} /glabel_0
Omega.(
    Import.(
        {join_or_1(" | ", import_functions_labels )}
    ) |
    Body.Region(0).(
        {join_or_1(" | ", global_function_nodes)} |
        {join_or_1(" | ", global_variable_nodes)}
    ) |
    Extra.DataTypes.(
        {join_or_1(" | ", data_types)}
    ) | 
    Export.Dedge{{label_write_main}}.Loc{{glabel_0}}
)
"""
    with open(new_file_name + ".json", "w") as f:
        json.dump(global_vars.strings_dict, f)

    
    with open(new_file_name + ".big", "w") as f:
        f.writelines(omega)

    print("ok")


if __name__ == "__main__":
    if len(sys.argv) == 2:
        main(sys.argv[1])
    else:
        print("No filename provided!")
    