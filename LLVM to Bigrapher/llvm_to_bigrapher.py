import llvmlite.binding as llvm
from llvmlite.ir.instructions import *


def main(file_name):
    llvm_bitcode = ""
    with open(file_name, "rb") as f:
        llvm_bitcode = f.read()

    llvm_module = llvm.parse_bitcode(llvm_bitcode)
    llvm_module.verify()
    for var in llvm_module.global_variables:
        print(var)

    for func in llvm_module.functions:
        for block in func.blocks:
            for instruction in block.instructions:
                match instruction.opcode:
                    case "load":
                        print(instruction)
                    case "add" | "sub" | "mul" | "shl" :
                        output_bigraph_simple_node(translate_instruction_quad(str(instruction)))
                    case _:
                        print("Not load")


def translate_instruction_quad(instruction):
    """
    Translate a typical integer arithmetic instruction with op-code, type, two operands,
    and up to two extra options.
    Instructions:
    add; sub; mul; shl

    Example:
    <result> = add <ty> <op1>, <op2>          ; yields ty:result
    <result> = add nuw <ty> <op1>, <op2>      ; yields ty:result
    <result> = add nsw <ty> <op1>, <op2>      ; yields ty:result
    <result> = add nuw nsw <ty> <op1>, <op2>  ; yields ty:result
    """
    instruction = instruction.split()
    instruction_info = {}
    instruction_info["opcode"] = instruction[2].capitalize()
    instruction_info["write"] = [ wordify(instruction[0]) ]
    instruction_info["read"] = [ wordify(instruction[-2]) , wordify(instruction[-1]) ]
    instruction_info["type"] = [ instruction[-3] ]
    if instruction[-4] != instruction[2]:
        instruction_info["options"] = [instruction[-4]]
        if instruction[-5] != instruction[2]:
            instruction_info["options"] += [instruction[-5]]
    else:
        instruction_info["options"] = []

    return instruction_info
    
def output_bigraph_simple_node(info):
    return\
f"""
Node.(
    NodeType.Simple |
    Body.{info["opcode"]} |
    Read.({" | ".join(info["read"])}) |
    Write.({" | ".join(info["write"])}) |
    Extra.(
        DataType.({" | ".join(info["type"])}) |
        Options.({" | ".join(info["options"])})    
    )
)
"""


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




main("example 2.bc")
    