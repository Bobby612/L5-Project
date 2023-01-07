import llvmlite.binding as llvm
from llvmlite.ir.instructions import *
from llvmlite.binding.value import ValueRef



def main(file_name):
    llvm_bitcode = ""
    with open(file_name, "rb") as f:
        llvm_bitcode = f.read()

    llvm_module = llvm.parse_bitcode(llvm_bitcode)
    llvm_module.verify()

    ipg = []
    cfg = []

    for function in llvm_module.functions :
        ## Body
        function_calls = []
        cfg_f = []
        for block in function.blocks:
            block_cfg, block_func_calls = function_cfg_node(block)
            cfg_f += [block_cfg]
            function_calls += block_func_calls

        ipg += [ function_ipg_node(function.name, function_calls) ]
        cfg += [ "( " + " | ".join(cfg_f) + " )"]

    
    print(ipg,"\n\n\n", cfg)


    # for var in llvm_module.global_variables:
    #     print(var)

    

    # for func in llvm_module.functions:
    #     for block in func.blocks:
    #         for instruction in block.instructions:
    #             print(instruction.opcode)
    #             # match instruction.opcode:
    #             #     case "load":
    #             #         print(instruction)
    #             #     case "add" | "sub" | "mul" | "shl" :
    #             #         output_bigraph_simple_node(translate_instruction_quad(str(instruction)))
    #             #     case _:
    #             #         print("Not load")


def function_cfg_node(block: ValueRef):
    entrance_register = ""
    exit_register = ""
    block_body = []
    dependent_func = []
    for instruction in block.instructions:
        entrance_register = "cfg_" + str(instruction).split()[0][1:]
        break
    
    for instruction in block.instructions:
        match instruction.opcode:
            case "add" | "sub" | "mul" | "shl" :
                block_body + [ output_bigraph_simple_node(translate_instruction_quad(str(instruction))) ]
            case "load":
                block_body + [ output_bigraph_simple_node(translate_instruction_load(str(instruction))) ]
            case "store":
                block_body + [ output_bigraph_simple_node(translate_instruction_store(str(instruction))) ]
            case "br":
                match translate_instruction_br(instruction):
                    case str(string):
                        exit_register = f"BlockExit{{{string}}}"
                    case tuple(tup):
                        brinstr, exit1, exit2 = tup
                        block_body += [ output_bigraph_simple_node(brinstr) ]
                        exit_register = f"BlockExit_ord(1){{{exit1}}} | BlockExit_ord(2){{{exit2}}}"
            case "call":
                instruction_str = str(instruction)
                start = instruction_str.find("@")
                end = instruction_str.find("(")
                dependent_func += [instruction_str[start+1:end]]


            case other:
                print(f"Unknown instruction {other}")

    return\
f"""
Block.(
    BlockEntry{{{entrance_register}}} |
    {exit_register} |
    Body.(
        {''' |
        '''.join(block_body)}
    )
)
""", dependent_func





def function_ipg_node(function_name, function_dependents):
    block_exit = []
    for dependent in function_dependents:
        block_exit += [ f"BlockExit{{ipg_{dependent}}}" ]
    if block_exit:
        block_exit = " | ".join(block_exit) + " | "
    else:
        block_exit = ""
    return\
f"""
Function.(
    BlockEntry{{ipg_{function_name}}} |
    {block_exit}
    CfgBlock{{cfg_ipg_{function_name}}}
)
"""
def translate_instruction_br(instruction):
    instruction = str(instruction)
    instruction = instruction.split()
    if instruction[1] == "i1":
        instruction_info = {}
        instruction_info["opcode"] = "Br"
        instruction_info["write"] = []
        instruction_info["read"] = [ wordify(instruction[2]) ]
        instruction_info["type"] = [  ]
        instruction_info["options"] = []
        return instruction_info, "cfg_" + instruction[4][1:-1], "cfg_" + instruction[6][1:]
    else:
        return "cfg_" + instruction[2][1:]


def translate_instruction_load(instruction):
    instruction = instruction.split()
    instruction_info = {}
    instruction_info["opcode"] = "Load"
    instruction_info["write"] = [ wordify(instruction[0]) ]
    instruction_info["read"] = [ wordify(instruction[-3]) ]
    instruction_info["type"] = [ instruction[3][:-1] ]
    instruction_info["options"] = []

    return instruction_info

def translate_instruction_store(instruction):
    instruction = instruction.split()
    instruction_info = {}
    instruction_info["opcode"] = "Store"
    instruction_info["write"] = [ wordify(instruction[-3]) ]
    instruction_info["read"] = [ wordify(instruction[2]) ]
    instruction_info["type"] = [ instruction[1] ]
    instruction_info["options"] = []

    return instruction_info

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
    