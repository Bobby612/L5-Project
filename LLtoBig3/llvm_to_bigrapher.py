import llvmlite.binding as llvm
from llvmlite.ir.instructions import *
from llvmlite.binding.value import ValueRef

def main(file_name):
    llvm_assembly = ""
    with open(file_name, "r") as f:
        llvm_assembly = f.read()

    llvm_module = llvm.parse_assembly(llvm_assembly)
    llvm_module.verify()

    for global_variable in llvm_module.global_variables:
        pass
        # print(parse_global_variable(global_variable)[0])
    
    for function in llvm_module.functions:
        print(parse_function(function)[0])

def parse_function(function: ValueRef):
    func_type = function.type
    export_name = function.name
    export = ["Adr(-1){state_address}"]
    closed_links = ["state_address"]
    if not str(func_type) == "void":
        export += ["Adr(-2){return_address}"]
        closed_links += ["return_address"]
    
    blocks = []
    labels = []
    addresses = []

    read_labels = []
    import_labels_adr = []


    for b in function.blocks:
        block, labels, address, cfg_node_entrance = parse_block(b, labels)
        blocks += [block]
        addresses += address
        closed_links += [cfg_node_entrance]
    
    labels = list(map(lambda x : x.replace("_","__").replace(".","_"), labels))
    import_function_itself = ""
    if not blocks:
        read_labels  += [f"Label(-1){{label_read_function_{export_name}}}"]
        import_function_itself = [f"label_read_function_{export_name}"]

    for i, l in enumerate(labels):
        read_labels += [f"Label({i}){{label_write_{l}}}"]
        import_labels_adr += [f"Label({i}){{label_import_{l}}}"]
        closed_links += [ f"label_import_{l}"]

    for a in addresses:
        import_labels_adr += [f"Adr({a[1:]}){{label_import_{a[1:]}}}"]
        closed_links += [f"label_import_{a[1:]}"]



    return \
f"""
{" /".join(closed_links)}
Node.(
    NodeType.Lambda |
    Read.({join_or_1(" | ", read_labels)}) |
    Import.({join_or_1(" | ", import_labels_adr)}) |
    Body.Region(0).(
        {join_or_1(''' |
        ''', blocks)}
    )
    Extra.(
        DataTypes.({transform_type(func_type)})
    )
    Export.({join_or_1(" | ", export)})
    Write.Label(0){{label_write_{export_name}}}
)
""", f"label_write_{export_name}", import_function_itself

def parse_block(block:ValueRef, labels:list):
    entrance_register = ""
    exit_register = ""
    state = 0

    function_addresses = []

    block_body = []
    import_address = set()
    import_labels = set()
    export_address = set()
    export_labels = set()

    closures = set()

    for instruction in block.instructions:
        e = int(str(instruction).split()[0][1:])
        entrance_register = "cfg_" + str(e-1)
        break

    for instruction in block.instructions:
        match instruction.opcode:
            case "add" | "sub" | "mul" | "shl" | "srem" | "urem" :
                instruction_node, closure = translate_instruction_quad(str(instruction))
                closures.add(closure)
                block_body += [ output_bigraph_simple_node(instruction_node) ]
            case "load":
                instruction_node, closure, load_address, is_label = translate_instruction_load(str(instruction))
                closures.add(closure)
                block_body += [ output_bigraph_simple_node(instruction_node) ]
                if is_label:
                    if store_address in labels:
                        import_labels.add((store_address, labels.index(store_address)))
                    else:
                        labels.append(store_address)
                        import_labels.add((store_address, labels.index(store_address)))
                else:
                    import_address.add(load_address)

            case "store":
                instruction_node, closure, store_address, is_label = translate_instruction_store(str(instruction))
                closures.add(closure)
                block_body += [ output_bigraph_simple_node(instruction_node) ]
                if is_label:
                    if store_address in labels:
                        export_labels.add((store_address, labels.index(store_address)))
                    else:
                        labels.append(store_address)
                        export_labels.add((store_address, labels.index(store_address)))
                else:
                    export_address.add(store_address)
                
            case "br":
                match translate_instruction_br(instruction):
                    case str(string):
                        exit_register = f"BlockExit{{{string}}} |"
                    case tuple(tup):
                        brinstr, closure, exit1, exit2 = tup
                        closures.add(closure)
                        block_body += [ output_bigraph_simple_node(brinstr) ]
                        exit_register = f"BlockExit_ord(1){{{exit1}}} | BlockExit_ord(2){{{exit2}}} |"
            case "call":
                instruction_string = str(instruction)
                i = instruction_string.index("@") + 1
                j = instruction_string.index("(")
                function_label = instruction_string[i:j]

                if function_label in labels:
                    import_labels.add((function_label, labels.index(function_label)))
                else:
                    labels.append(function_label)
                    import_labels.add((function_label, labels.index(function_label)))
                instruction_node, closure, label = translate_instruction_call_complex(instruction, function_label, state)
                block_body += instruction_node
                closures.add(closure)

                for l in label:
                    if l in labels:
                        import_labels.add((l, labels.index(l)))
                    else:
                        labels.append(l)
                        import_labels.add((l, labels.index(l)))


                block_body += [ output_bigraph_simple_node(instruction_node) ]

                state += 0

            case "icmp":
                instruction_node, closure = translate_instruction_icmp(str(instruction))
                closures.add(closure)
                block_body += [ output_bigraph_simple_node(instruction_node) ]
            case "ret":
                instruction_node, closure = translate_instruction_ret(str(instruction))
                closures.add(closure)
                block_body += [ output_bigraph_simple_node(instruction_node) ]
            case "bitcast":
                instruction_node, closure = translate_instruction_bitcast(str(instruction))
                closures.add(closure)
                block_body += [ output_bigraph_simple_node(instruction_node) ]
            case "alloca":
                instruction_node, closure, function_address = translate_instruction_alloca(str(instruction))
                closures.add(closure)
                block_body += [ output_bigraph_simple_node(instruction_node) ]
                function_addresses.append(function_address)
            case other:
                print(f"Unknown instruction {other}")

    import_address = list(import_address)
    import_address = list(map(create_address2, import_address))
    import_labels = list(import_labels)
    import_labels = list(map(create_label2, import_labels))

    export_address = list(export_address)
    export_address = list(map(create_address2, export_address))
    export_labels = list(export_labels)
    export_labels = list(map(create_label2, export_labels))
    return\
f"""
{" ".join(list(closures))}
Block.(
    BlockEntry{{{entrance_register}}} |
    {exit_register}
    Import.({join_or_1(" | ", import_address + import_labels)})
    Body.Region(0).(
        {join_or_1(''' |
        ''', block_body)}
    )
    Export.({join_or_1(" | ", export_address + export_labels)})

)
""", labels, function_addresses, entrance_register

def create_address2(address):
    if address[-1] not in "1234567890":
        address = address[:-1]
    return create_address("%" + address,int(address))[0]

def create_label2(label):
    return create_address("@" + label[0].replace("_","__").replace(".", "_"), label[1])[0]

def translate_instruction_call_complex(instruction:ValueRef, name:str, state:int):
    instruction_2_split = str(instruction).split(name)
    call_info = instruction_2_split[0]
    closures = f" /state_{state}"
    labels = []

    instruction_info = {}
    instruction_info["opcode"] = "Call"
    instruction_info["write"] = [f"State{{state_{state+1}}}"]
    if call_info[0][0] == "%":
        adr, closure = create_address(call_info[0])
        closures += closure
        instruction_info["write"] += [ adr ]
        
    
    instruction_info["type"] = []
    instruction_info["read"] = [ f"State{{state_{state}}}" ]
    j = 0
    gep = False
    gep_expr = ""
    for i in instruction_2_split[1].split():
        if i[0] == "@":
            adr, closure = create_address(i,j)
            closures += closure
            instruction_info["read"] += [ adr ]
            labels += [i[:-1]]
        if j%2 == 0:
            instruction_info["type"] += [transform_type(i,j)]
            j += 1
        else:
            if not gep:
                if i == "getelementptr":
                    gep = True
                    gep_expr += i
                else:
                    adr, closure = create_address(i,j)
                    closures += closure
                    instruction_info["read"] += [ adr ]
                    j += 1
            else:
                if i[-1] == ")" or i[-2:] == "),":
                    gep = False
                    instruction_info["read"] += [ f'Const({j},"{gep_expr + i}")' ]
                    gep_expr = ""
                    j += 1
                else:
                    gep_expr += i


    
    instruction_info["type"] += [ transform_type(instruction.type) ]
    instruction_info["options"] = []

    return instruction_info, closure, labels



def parse_global_variable(global_variable:ValueRef):
    globa_variable_str = str(global_variable)
    export_name = global_variable.name
    export_name = export_name.replace("_", "__").replace(".", "_")
    var_type = str(global_variable.type)[:-1]

    options = globa_variable_str.split(var_type)[0].split("=")[1].split()
    options = list(map(transform_option, options))
    alignment = globa_variable_str.split(",")[-1]
    options += [ transform_alignment(alignment) ]

    if var_type[-1] == "*":
        info, import_name = translate_instruction_getelementptr_asconst(globa_variable_str.split(var_type)[-1])
        info["read"] += [f"label_import_{import_name}"]
        info["write"] += [f"label_export_{export_name}"]
        return \
f"""
/label_export{export_name} /label_import_{import_name}
Node.(
    NodeType.Delta |
    Read.Label(0){{label_write_{import_name}}} |
    Import.Label(0){{label_import_{import_name}}} |
    Body.Region(0).(
        {output_bigraph_simple_node(info)}
    Extra.(
        DataTypes.({transform_type(var_type)}) |
        Options.({join_or_1(" | ",options)})    
    )
    Export.Label(0){{label_export_{export_name}}} |
    Write.Label(0){{label_write_{export_name}}}
)
""",  f"label_write_{export_name}"    

    else:
        literal = globa_variable_str.split(var_type)[-1]
        return \
f"""
/label_export{export_name}
Node.(
    NodeType.Delta |
    Read.1 |
    Import.1 |
    Body.Region(0).(
        Node.(
            NodeType.Simple |
            Body.Literal |
            Read.1 |
            Write.(Label(0){{label_export_{export_name}}}) |
            Extra.(
                DataTypes.()) |
                Options.({transform_option(literal)})
            )
    Extra.(
        DataTypes.({transform_type(var_type)}) |
        Options.({join_or_1(" | ",options)})    
    )
    Export.Label(0){{label_export_{export_name}}} |
    Write.Label(0){{label_write_{export_name}}}
)
""", f"/label_write_{export_name}"
    




    

def main2(file_name):
    llvm_assembly = ""
    with open(file_name, "r") as f:
        llvm_assembly = f.read()

    llvm_module = llvm.parse_assembly(llvm_assembly)
    llvm_module.verify()

    ipg = []
    cfg = []
    top_level_closures = set()

    for function in llvm_module.functions :
        ## Body
        function_calls = []
        cfg_f = []
        closures = " "
        top_level_closures.update({ f" /cfg_ipg_{function.name}", f" /ipg_{function.name}" } )
        for block in function.blocks:
            block_cfg, block_func_calls, closure, tl_closure = function_cfg_node(block)
            closures += closure
            top_level_closures.update(tl_closure)
            cfg_f += [block_cfg]
            function_calls += block_func_calls

        
        function_reads = []
        # For now function types don't work
        function_types = [] # [transform_type(function.type)]

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
    
    bigraph = " ".join(top_level_closures) + "(\n" + ipg + "\n||\n" + cfg + "\n)"
    bigraph = bigraph.replace("*", "x")
    print(bigraph)


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
    top_level_closures = set()
    for instruction in block.instructions:
        e = int(str(instruction).split()[0][1:])
        entrance_register = "cfg_" + str(e-1)
        top_level_closures.update({" /" + entrance_register})
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
                        top_level_closures.update({ " /" + string })
                    case tuple(tup):
                        brinstr, closure, exit1, exit2 = tup
                        closures += closure
                        top_level_closures.update({ " /" + exit1, " /" + exit2})
                        block_body += [ output_bigraph_simple_node(brinstr) ]
                        exit_register = f"BlockExit_ord(1){{{exit1}}} | BlockExit_ord(2){{{exit2}}} |"
            case "call":
                instruction_string = str(instruction)
                i = instruction_string.index("@") + 1
                j = instruction_string.index("(") 
                dependent_func += [instruction_string[i:j]]

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
""", dependent_func, closures, top_level_closures





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

def translate_instruction_call(instruction, state):
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

    instruction_info["read"] += [ f"State{{state_{state}}}" ]
    instruction_info["write"] += [ f"State{{state_{state+1}}}"]
    
    
    call_index -= 1
    while call_index >= 0 and instruction[call_index] != "=":
        instruction_info["options"] += [transform_option(instruction[call_index])]
        call_index -= 1
    
    return instruction_info, closures

def translate_instruction_getelementptr(instruction):
    return instruction

        
def translate_instruction_getelementptr_asconst(instruction):
    instruction_info = {}
    instruction_info["opcode"] = "GetElementPtrConst"
    instruction_info["write"] = []
    instruction_info["read"] = [ ]
    instruction_info["type"] = [  ]
    instruction_info["options"] = []
    return instruction_info, instruction.split("@")[1].split(",")[0].replace("_", "__").replace(".", "_")

def translate_instruction_alloca(instruction):
    instruction = instruction.split()
    instruction_info = {}
    instruction_info["opcode"] = "Alloca"
    write_address, closure = create_address(instruction[0])
    instruction_info["write"] = [write_address]
    instruction_info["read"] = [ ]
    instruction_info["type"] = [ transform_type(instruction[3][:-1])  ]
    instruction_info["options"] = []
    return instruction_info, closure, instruction[0][1:]

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
    instruction_info["type"] = [ transform_type(instruction[3], 1), transform_type(instruction[6], 2) ]
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

    label = False
    if instruction[-3][0] == "@":
        label = True

    return instruction_info, closures, instruction[-3][1:], label

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

    label = False
    if instruction[-3][0] == "@":
        label = True

    return instruction_info, closures, instruction[-3][1:], label

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

def transform_alignment(alignment_string):
    return f"Alignment(\"{alignment_string}\")"

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

    if not str.isdigit(number_string[-1]):
        number_string = number_string[:-1]
    
    return f"Const({order},{number_string})", ""

def join_or_1(join_string, join_list):
    ret = join_string.join(join_list)
    if not ret:
        return "1"
    else:
        return ret

main("example 3.ll")
    