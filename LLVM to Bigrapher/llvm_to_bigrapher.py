import llvmlite.binding as llvm
from llvmlite.ir.instructions import *

llvm_bitcode = ""
with open("example 2.bc", "rb") as f:
    llvm_bitcode = f.read()

llvm_module = llvm.parse_bitcode(llvm_bitcode)
llvm_module.verify()
for var in llvm_module.global_variables:
    print(var)


def translate_instruction_add(instruction):
    instruction = instruction.split()
    instruction_info = {}
    instruction_info["opcode"] = "Add"
    instruction_info["write"] = [ wordify(instruction[0]) ]
    instruction_info["read"] = [ wordify(instruction[-2]) , wordify(instruction[-1]) ]
    instruction_info["type"] = [ instruction[-3] ]
    if instruction[-4] != "add":
        instruction_info["options"] = [instruction[-4]]
    if instruction[-5] != "add":
        instruction_info["options"] += [instruction[-5]]

    return instruction_info
    
def output_bigraph_simple_node(info):
    print(\
f"""
Node.(
    Opcode.{info["opcode"]} |
    Read.({" | ".join(info["read"])}) |
    Write.({" | ".join(info["write"])}) |
    Type.({" | ".join(info["type"])}) |
    Options.({" | ".join(info["options"])})
)
""")


def wordify(number_string):
    return_string = ""
    if number_string[0] != "%":
        return f"Const({number_string})"
    
    for i in number_string:
        if i == '0':
            return_string += "zero"
        elif i == '1':
            return_string += "one"
        elif i == "2":
            return_string += "two"
        elif i == "3":
            return_string += "three"
        elif i == "4":
            return_string += "four"
        elif i == "5":
            return_string += "five"
        elif i == "6":
            return_string += "six"
        elif i == "7":
            return_string += "seven"
        elif i == "8":
            return_string += "eight"
        elif i == "9":
            return_string += "nine"
    return f"Adr{{{return_string}}}"

for func in llvm_module.functions:
    for block in func.blocks:
        for instruction in block.instructions:
            match instruction.opcode:
                case "load":
                    print(instruction)
                case "add":
                    output_bigraph_simple_node(translate_instruction_add(str(instruction)))
                case _:
                    print("Not load")



    