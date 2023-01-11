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
        cfg += [ f"Cfgf{{cfg_ipg_{function.name}}}.( " + " | ".join(cfg_f) + " )"]

    ipg = "Ipg.(\n" \
        + " |\n".join(ipg) \
        + "    )"

    cfg = "Cfg.(\n" \
        + " |\n".join(cfg) \
        + "    )"
    
    print(ipg + "\n||\n" + cfg)


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
        e = int(str(instruction).split()[0][1:])
        entrance_register = "cfg_" + str(e-1)
        break
    
    for instruction in block.instructions:
        match instruction.opcode:
            case "add" | "sub" | "mul" | "shl" | "srem" | "urem" :
                block_body += [ output_bigraph_simple_node(translate_instruction_quad(str(instruction))) ]
            case "load":
                block_body += [ output_bigraph_simple_node(translate_instruction_load(str(instruction))) ]
            case "store":
                block_body += [ output_bigraph_simple_node(translate_instruction_store(str(instruction))) ]
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

            case "icmp":
                block_body += [ output_bigraph_simple_node(translate_instruction_icmp(str(instruction))) ]
            case "ret":
                block_body += [ output_bigraph_simple_node(translate_instruction_ret(str(instruction))) ]
            case "bitcast":
                block_body += [ output_bigraph_simple_node(translate_instruction_bitcast(str(instruction))) ]
            case "alloca":
                block_body += [ output_bigraph_simple_node(translate_instruction_alloca(str(instruction))) ]
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

    # instruction_info = {}
    # instruction_info["opcode"] = ""
    # instruction_info["write"] = []
    # instruction_info["read"] = [ ]
    # instruction_info["type"] = [  ]
    # instruction_info["options"] = []

def translate_instruction_alloca(instruction):
    instruction = instruction.split()
    instruction_info = {}
    instruction_info["opcode"] = "Alloca"
    instruction_info["write"] = [create_address(instruction[0])]
    instruction_info["read"] = [ ]
    instruction_info["type"] = [ transform_type(instruction[3][:-1])  ]
    instruction_info["options"] = []
    return instruction_info

def translate_instruction_bitcast(instruction):
    instruction = instruction.split()
    instruction_info = {}
    instruction_info["opcode"] = "Bitcast"
    instruction_info["write"] = [create_address(instruction[0])]
    instruction_info["read"] = [create_address(instruction[4])]
    instruction_info["type"] = [ transform_type(instruction[4], 1), transform_type(instruction[6], 2) ]
    instruction_info["options"] = []
    return instruction_info



def translate_instruction_ret(instruction):
    instruction = instruction.split()
    instruction_info = {}
    instruction_info["opcode"] = "Ret"
    instruction_info["write"] = []
    instruction_info["read"] = [ create_address(instruction[2]) ]
    instruction_info["type"] = [ transform_type(instruction[1])  ]
    instruction_info["options"] = []
    return instruction_info


def translate_instruction_icmp(instruction):
    instruction = instruction.split()
    instruction_info = {}
    instruction_info["opcode"] = "Icmp"
    instruction_info["write"] = [create_address(instruction[0])]
    instruction_info["read"] = [ create_address(instruction[-2], 1), create_address(instruction[-1], 2)]
    instruction_info["type"] = [ transform_type(instruction[4]) ]
    instruction_info["options"] = [transform_option(instruction[3])]
    return instruction_info

def translate_instruction_br(instruction):
    instruction = str(instruction)
    instruction = instruction.split()
    if instruction[1] == "i1":
        instruction_info = {}
        instruction_info["opcode"] = "Br"
        instruction_info["write"] = []
        instruction_info["read"] = [ create_address(instruction[2]) ]
        instruction_info["type"] = [  ]
        instruction_info["options"] = []
        return instruction_info, "cfg_" + instruction[4][1:-1], "cfg_" + instruction[6][1:]
    else:
        return "cfg_" + instruction[2][1:]


def translate_instruction_load(instruction):
    instruction = instruction.split()
    instruction_info = {}
    instruction_info["opcode"] = "Load"
    instruction_info["write"] = [ create_address(instruction[0]) ]
    instruction_info["read"] = [ create_address(instruction[-3]) ]
    instruction_info["type"] = [ transform_type(instruction[3][:-1], 1), transform_type(instruction[4], 2) ]
    instruction_info["options"] = []

    return instruction_info

def translate_instruction_store(instruction):
    instruction = instruction.split()
    instruction_info = {}
    instruction_info["opcode"] = "Store"
    instruction_info["write"] = [ create_address(instruction[-3]) ]
    instruction_info["read"] = [ create_address(instruction[2]) ]
    instruction_info["type"] = [ transform_type(instruction[1], 1), transform_type(instruction[3], 2)]
    instruction_info["options"] = []

    return instruction_info

def translate_instruction_quad(instruction):
    """
    Translate a typical integer arithmetic instruction with op-code, type, two operands,
    and up to two extra options.
    Instructions:
    add; sub; mul; shl; srem; urem

    Example:
    <result> = add <ty> <op1>, <op2>          ; yields ty:result
    <result> = add nuw <ty> <op1>, <op2>      ; yields ty:result
    <result> = add nsw <ty> <op1>, <op2>      ; yields ty:result
    <result> = add nuw nsw <ty> <op1>, <op2>  ; yields ty:result
    """
    instruction = instruction.split()
    instruction_info = {}
    instruction_info["opcode"] = instruction[2].capitalize()
    instruction_info["write"] = [ create_address(instruction[0]) ]
    instruction_info["read"] = [ create_address(instruction[-2], 1) , create_address(instruction[-1], 2) ]
    instruction_info["type"] = [ transform_type(instruction[-3]) ]
    if instruction[-4] != instruction[2]:
        instruction_info["options"] = [transform_option(instruction[-4])]
        if instruction[-5] != instruction[2]:
            instruction_info["options"] += [transform_option(instruction[-5])]
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
        DataTypes.({" | ".join(info["type"])}) |
        Options.({" | ".join(info["options"])})    
    )
)
"""

def transform_type(type_string, type_order=-1):
    return f"DataType({type_order},\"{type_string}\")"

def transform_option(option_string):
    return f"Option(\"{option_string}\")"

def create_address(number_string, order=-1):
    return_string = ""
    if number_string[0] == "@":
        label = "label_" + number_string[1:-1]
        return f"Label{{{label}}}"        
    
    if number_string[0] == "%":
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
        return f"Adr({order}){{{return_string}}}"

    return f"Const({number_string})"



main("example 2.bc")
    