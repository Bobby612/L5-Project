import llvmlite.binding as llvm
from llvmlite.ir.instructions import *
from llvmlite.binding.value import ValueRef



def main(file_name):
    llvm_assembly = ""
    with open(file_name, "r") as f:
        llvm_assembly = f.read()

    llvm_module = llvm.parse_assembly(llvm_assembly)
    llvm_module.verify()

    ipg = []
    cfg = []

    for function in llvm_module.functions :
        ## Body
        function_calls = []
        cfg_f = []
        closures = " "
        for block in function.blocks:
            block_cfg, block_func_calls, closure = function_cfg_node(block)
            closures += closure
            cfg_f += [block_cfg]
            function_calls += block_func_calls

        
        function_reads = []
        function_types = [transform_type(function.type)]

        for n, argument in enumerate(function.arguments):
            argument = str(argument).split()
            read_address, closure = create_address(argument[1], n)
            closures += closure
            function_reads += [read_address]
            function_types += [transform_type(argument[0], n)]
        
        closures = set(closures.split())

        ipg += [ function_ipg_node(function, function_calls) ]
        cfg += [ " ".join(closures) + "\n" \
             + f"Cfgf{{cfg_ipg_{function.name}}}.( \n"\
             + "Read.(" + join_or_1(" | ", function_reads) + ") |\n" \
             + "DataTypes.(" + join_or_1(" | ",function_types) + ") |\n" \
             + join_or_1(" | ",cfg_f) + " )"]

    ipg = "Ipg.(\n" \
        + join_or_1(" |\n",ipg) \
        + "    )"

    cfg = "Cfg.(\n" \
        + join_or_1(" |\n",cfg) \
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
    closures = " "
    for instruction in block.instructions:
        match instruction.opcode:
            case "add" | "sub" | "mul" | "shl" | "srem" | "urem" :
                instruction_node, closure = translate_instruction_quad(str(instruction))
                closures += closure
                block_body += [ output_bigraph_simple_node(instruction_node) ]
            case "load":
                instruction_node, closure = translate_instruction_load(str(instruction))
                closures += closure
                block_body += [ output_bigraph_simple_node(instruction_node) ]
            case "store":
                instruction_node, closure = translate_instruction_store(str(instruction))
                closures += closure
                block_body += [ output_bigraph_simple_node(instruction_node) ]
            case "br":
                match translate_instruction_br(instruction):
                    case str(string):
                        exit_register = f"BlockExit{{{string}}} |"
                    case tuple(tup):
                        brinstr, closure, exit1, exit2 = tup
                        closures += closure
                        block_body += [ output_bigraph_simple_node(brinstr) ]
                        exit_register = f"BlockExit_ord(1){{{exit1}}} | BlockExit_ord(2){{{exit2}}} |"
            case "call":
                dependent_func += [instruction.name]
                instruction_node, closure = translate_instruction_call(str(instruction))
                closures += closure
                block_body += [ output_bigraph_simple_node(instruction_node) ]

            case "icmp":
                instruction_node, closure = translate_instruction_icmp(str(instruction))
                closures += closure
                block_body += [ output_bigraph_simple_node(instruction_node) ]
            case "ret":
                instruction_node, closure = translate_instruction_ret(str(instruction))
                closures += closure
                block_body += [ output_bigraph_simple_node(instruction_node) ]
            case "bitcast":
                instruction_node, closure = translate_instruction_bitcast(str(instruction))
                closures += closure
                block_body += [ output_bigraph_simple_node(instruction_node) ]
            case "alloca":
                instruction_node, closure = translate_instruction_alloca(str(instruction))
                closures += closure
                block_body += [ output_bigraph_simple_node(instruction_node) ]
            case other:
                print(f"Unknown instruction {other}")

    return\
f"""
Block.(
    BlockEntry{{{entrance_register}}} |
    {exit_register}
    Body.(
        {join_or_1(''' |
        ''',block_body)}
    )
)
""", dependent_func, closures





def function_ipg_node(function: ValueRef, function_dependents):
    function_name = function.name
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

def translate_instruction_call(instruction):
    instruction = instruction.replace("("," ").split()
    call_index = instruction.index("call")
    instruction_info = {}
    if instruction[call_index+1] == "noalias":
        type_index = call_index + 2
        instruction_info["options"] = [ transform_option("noalias")]
    else:
        type_index = call_index + 1
        instruction_info["options"] = [ ]

    
    instruction_info["opcode"] = "Call"
    closures = ""
    if instruction[0][0] == "%":
        write_address, closure = create_address(instruction[0])
        closures += closure
        instruction_info["write"] = [write_address]
    else:
        instruction_info["write"] = []
    instruction_info["type"] = [ transform_type(instruction[type_index]) ]
    read_address, closure = create_address(instruction[type_index+1], 0)
    closures += closure
    instruction_info["read"] = [ read_address ]
    for n, i in enumerate(instruction[type_index + 2:]):
        if i[0] == "#":
            break
        if n%2 == 0:
            instruction_info["type"] += [transform_type(i, n+1)]
        else:
            read_address, closure = create_address(i[:-1], n)
            closures += closure
            instruction_info["read"] += [read_address]
    
    
    call_index -= 1
    while call_index >= 0 and instruction[call_index] != "=":
        instruction_info["options"] += [transform_option(instruction[call_index])]
        call_index -= 1
    
    return instruction_info, closure

def translate_instruction_alloca(instruction):
    instruction = instruction.split()
    instruction_info = {}
    instruction_info["opcode"] = "Alloca"
    write_address, closure = create_address(instruction[0])
    instruction_info["write"] = [write_address]
    instruction_info["read"] = [ ]
    instruction_info["type"] = [ transform_type(instruction[3][:-1])  ]
    instruction_info["options"] = []
    return instruction_info, closure

def translate_instruction_bitcast(instruction):
    instruction = instruction.split()
    instruction_info = {}
    instruction_info["opcode"] = "Bitcast"
    closures = ""
    write_address, closure = create_address(instruction[0])
    closures += closure
    instruction_info["write"] = [write_address]
    read_address, closure = create_address(instruction[4])
    closures += closure
    instruction_info["read"] = [read_address]
    instruction_info["type"] = [ transform_type(instruction[4], 1), transform_type(instruction[6], 2) ]
    instruction_info["options"] = []
    return instruction_info, closures



def translate_instruction_ret(instruction):
    instruction = instruction.split()
    instruction_info = {}
    instruction_info["opcode"] = "Ret"
    instruction_info["write"] = []
    read_address, closure = create_address(instruction[2])
    instruction_info["read"] = [ read_address ]
    instruction_info["type"] = [ transform_type(instruction[1])  ]
    instruction_info["options"] = []
    return instruction_info, closure


def translate_instruction_icmp(instruction):
    instruction = instruction.split()
    instruction_info = {}
    instruction_info["opcode"] = "Icmp"
    closures = ""
    write_address, closure = create_address(instruction[0])
    closures += closure
    instruction_info["write"] = [write_address]
    read_address1, closure = create_address(instruction[-2], 1)
    closures += closure
    read_address2, closure = create_address(instruction[-1], 2)
    closures += closure
    instruction_info["read"] = [ read_address1 , read_address2]
    instruction_info["type"] = [ transform_type(instruction[4]) ]
    instruction_info["options"] = [transform_option(instruction[3])]
    return instruction_info, closures

def translate_instruction_br(instruction):
    instruction = str(instruction)
    instruction = instruction.split()
    if instruction[1] == "i1":
        instruction_info = {}
        instruction_info["opcode"] = "Br"
        instruction_info["write"] = []
        closures = ""
        read_address, closure = create_address(instruction[2])
        closures += closure
        instruction_info["read"] = [ read_address ]
        instruction_info["type"] = [  ]
        instruction_info["options"] = []
        return instruction_info, closures, "cfg_" + instruction[4][1:-1], "cfg_" + instruction[6][1:]
    else:
        return "cfg_" + instruction[2][1:]


def translate_instruction_load(instruction):
    instruction = instruction.split()
    instruction_info = {}
    instruction_info["opcode"] = "Load"
    closures = ""
    write_addres, closure = create_address(instruction[0])
    closures += closure
    instruction_info["write"] = [ write_addres  ]
    read_address, closure = create_address(instruction[-3])
    closures += closure
    instruction_info["read"] = [ read_address ]
    instruction_info["type"] = [ transform_type(instruction[3][:-1], 1), transform_type(instruction[4], 2) ]
    instruction_info["options"] = []

    return instruction_info, closures

def translate_instruction_store(instruction):
    instruction = instruction.split()
    instruction_info = {}
    instruction_info["opcode"] = "Store"
    closures = ""
    write_addres, closure = create_address(instruction[-3]) 
    closures += closure
    instruction_info["write"] = [ write_addres ]
    read_addres, closure = create_address(instruction[2])
    closures += closure
    instruction_info["read"] = [ read_addres ]
    instruction_info["type"] = [ transform_type(instruction[1], 1), transform_type(instruction[3], 2)]
    instruction_info["options"] = []

    return instruction_info, closures

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
    write_address, closure = create_address(instruction[0])
    closures = ""
    closures += closure
    instruction_info["write"] = [ write_address ]
    read_address1, closure = create_address(instruction[-2], 1)
    closures += closure
    read_address2, closure = create_address(instruction[-1], 2)
    closures+= closure
    instruction_info["read"] = [ read_address1 , read_address2 ]
    instruction_info["type"] = [ transform_type(instruction[-3]) ]
    if instruction[-4] != instruction[2]:
        instruction_info["options"] = [transform_option(instruction[-4])]
        if instruction[-5] != instruction[2]:
            instruction_info["options"] += [transform_option(instruction[-5])]
    else:
        instruction_info["options"] = []

    return instruction_info, closures
    
def output_bigraph_simple_node(info):
    return\
f"""
Node.(
    NodeType.Simple |
    Body.{info["opcode"]} |
    Read.({join_or_1(" | ",info["read"])}) |
    Write.({join_or_1(" | ",info["write"])}) |
    Extra.(
        DataTypes.({join_or_1(" | ",info["type"])}) |
        Options.({join_or_1(" | ",info["options"])})    
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
        if number_string[-1] == ",":
            number_string = number_string[:-1]
        label = "label_" + number_string[1:]
        return f"Label({order}){{{label}}}", " /" + label    
    
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
        return f"Adr({order}){{{return_string}}}", " /" + return_string

    return f"Const({order},{number_string})", ""

def join_or_1(join_string, join_list):
    ret = join_string.join(join_list)
    if not ret:
        return "1"
    else:
        return ret

main("example 2.ll")
    