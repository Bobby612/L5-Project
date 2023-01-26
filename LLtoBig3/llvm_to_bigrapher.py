import llvmlite.binding as llvm
from llvmlite.ir.instructions import *
from llvmlite.binding.value import ValueRef
import json

strings_dict = {}

def main(file_name):
    llvm_assembly = ""
    with open(file_name, "r") as f:
        llvm_assembly = f.read()

    llvm_module = llvm.parse_assembly(llvm_assembly)
    llvm_module.verify()

    import_functions = []
    global_function_nodes = []
    global_variable_nodes = []
    global_links = []


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

    import_functions_labels = list(map(create_label3, list(enumerate(import_functions))))
    import_labels = list(map(lambda x : "/" + x, import_functions + global_links))

    omega = \
f"""
{" ".join(import_labels)}
Omega.(
    Import.(
        {join_or_1(" | ", import_functions_labels )}
    ) |
    Body.Region(0).(
        {join_or_1(" | ", global_function_nodes)} |
        {join_or_1(" | ", global_variable_nodes)}
    ) |
    Export.Label(0){{label_write_main}}
)
"""
    with open("string_json.json", "w") as f:
        json.dump(strings_dict, f)
    print(omega)


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
    
    # labels = list(map(lambda x : x.replace("_","__").replace(".","_"), labels))
    import_function_itself = ""
    if not blocks:
        read_labels  += [f"Label(-1){{label_read_function_{export_name}}}"]
        import_function_itself = f"label_read_function_{export_name}"

    for i, l in enumerate(labels):
        read_labels += [f"Label({i}){{label_write_{l}}}"]
        import_labels_adr += [f"Label({i}){{label_import_{l}}}"]
        closed_links += [ f"label_import_{l}"]

    for a in addresses:
        import_labels_adr += [f"Adr({a}){{label_import_{a}}}"]
        closed_links += [f"label_import_{a}"]



    return \
f"""
{" ".join( list(map(lambda x: "/" + x, closed_links)))}
Node.(
    NodeType.Lambda |
    Read.({join_or_1(" | ", read_labels)}) |
    Import.({join_or_1(" | ", import_labels_adr)}) |
    Body.Region(0).(
        {join_or_1(''' |
        ''', blocks)}
    ) |
    Extra.DataTypes.({transform_type(func_type)}
    ) |
    Export.({join_or_1(" | ", export)}) |
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
                closures.update(closure)
                block_body += [ output_bigraph_simple_node(instruction_node) ]
            case "load":
                instruction_node, closure, load_address, is_label = translate_instruction_load(str(instruction))
                closures.update(closure)
                block_body += [ output_bigraph_simple_node(instruction_node) ]
                if is_label:
                    if load_address in labels:
                        import_labels.add((load_address, labels.index(load_address)))
                    else:
                        labels.append(load_address)
                        import_labels.add((load_address, labels.index(load_address)))
                else:
                    import_address.add(load_address)

            case "store":
                instruction_node, closure, store_address, is_label = translate_instruction_store(str(instruction))
                closures.update(closure)
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
                        exit_register = f" | BlockExit{{{string}}}"
                    case tuple(tup):
                        brinstr, closure, exit1, exit2 = tup
                        closures.update(closure)
                        block_body += [ output_bigraph_simple_node(brinstr) ]
                        exit_register = f" | BlockExit_ord(1){{{exit1}}} | BlockExit_ord(2){{{exit2}}}"
            case "call":
                instruction_string = str(instruction)
                i = instruction_string.index("@") + 1
                j = instruction_string.index("(")
                function_label = instruction_string[i:j].replace("_","__").replace(".","_")

                if function_label in labels:
                    import_labels.add((function_label, labels.index(function_label)))
                else:
                    labels.append(function_label)
                    import_labels.add((function_label, labels.index(function_label)))
                    closures.add("/label_" + function_label)
                instruction_node, closure, label = translate_instruction_call_complex(instruction, function_label, state)
                
                closures.update(closure)

                for l in label:
                    if l in labels:
                        import_labels.add((l, labels.index(l)))
                    else:
                        labels.append(l)
                        import_labels.add((l, labels.index(l)))


                block_body += [ output_bigraph_simple_node(instruction_node) ]

                state += 1

            case "icmp":
                instruction_node, closure = translate_instruction_icmp(str(instruction))
                closures.update(closure)
                block_body += [ output_bigraph_simple_node(instruction_node) ]
            case "ret":
                instruction_node, closure = translate_instruction_ret(str(instruction))
                closures.update(closure)
                block_body += [ output_bigraph_simple_node(instruction_node) ]
            case "bitcast":
                instruction_node, closure = translate_instruction_bitcast(str(instruction))
                closures.update(closure)
                block_body += [ output_bigraph_simple_node(instruction_node) ]
            case "alloca":
                instruction_node, closure, function_address = translate_instruction_alloca(str(instruction))
                closures.update(closure)
                block_body += [ output_bigraph_simple_node(instruction_node) ]
                function_addresses.append(function_address)
            case "getelementptr":
                instruction_node, closure = translate_instruction_getelementptr(instruction)
                closures.update(closure)
                block_body += [ output_bigraph_simple_node(instruction_node)]
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
{" ".join(list(closures))} /state_{state}
Block.(
    Interface.(
        BlockEntry{{{entrance_register}}} 
        {exit_register}
    ) |
    Import.({join_or_1(" | ", import_address + import_labels + [f"State{{state_0}}"])}) |
    Body.Region(0).(
        {join_or_1(''' |
        ''', block_body)}
    ) |
    Export.({join_or_1(" | ", export_address + export_labels + [f"State{{state_{state}}}"])})

)
""", labels, function_addresses, entrance_register

def create_address2(address):
    if address[-1] not in "1234567890":
        address = address[:-1]
    return create_address("%" + address,int(address))[0]

def create_label2(label):
    return f"Label({label[1]}){{label_{label[0]}}}"

def create_label3(label):
    return f"Label({label[0]}){{{label[1]}}}"

def translate_instruction_call_complex(instruction:ValueRef, name:str, state:int):
    instruction_2_split = str(instruction).split(name)
    call_info = instruction_2_split[0]
    closures = [f" /state_{state}"]
    labels = []

    instruction_info = {}
    instruction_info["opcode"] = "Call"
    instruction_info["write"] = [f"State{{state_{state+1}}}"]
    if call_info[0][0] == "%":
        adr, closure = create_address(call_info[0])
        closures += [closure]
        instruction_info["write"] += [ adr ]
        
    
    instruction_info["type"] = []
    instruction_info["read"] = [ f"State{{state_{state}}}" ]
    j = 0
    gep = False
    gep_expr = ""
    for i in instruction_2_split[1].split():
        if i[0] == "@":
            adr, closure = create_address(i,j)
            closures += [closure]
            instruction_info["read"] += [ adr ]
            labels += [closure[8:]]
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
                    closures += [closure]
                    instruction_info["read"] += [ adr ]
                    j += 1
            else:
                if i[-1] == ")" or i[-2:] == "),":

                    current_string = gep_expr + i
                    if current_string in strings_dict:
                        type_no = strings_dict[current_string]
                    else:
                        type_no = len(strings_dict)
                        strings_dict[current_string] = type_no

                    gep = False
                    instruction_info["read"] += [ f'Const({j},{type_no})' ]
                    gep_expr = ""
                    j += 1
                else:
                    gep_expr += i


    
    instruction_info["type"] += [ transform_type(instruction.type) ]
    instruction_info["options"] = []

    return instruction_info, closures, labels



def parse_global_variable(global_variable:ValueRef):
    globa_variable_str = str(global_variable)
    export_name = global_variable.name
    export_name = export_name.replace("_", "__").replace(".", "_")
    var_type = str(global_variable.type)[:-1]

    options = globa_variable_str.split(var_type)[0].split("=")[1].split()
    options = list(map(transform_option, options))
    alignment = globa_variable_str.split(",")[-1]
    options += [ transform_alignment(alignment) ]


    literal = globa_variable_str.split(var_type)[-1]

    if literal in strings_dict:
        type_no = strings_dict[literal]
    else:
        type_no = len(strings_dict)
        strings_dict[literal] = type_no
    
    if var_type[-1] == "*":
        
        import_name = globa_variable_str.split(var_type)[-1].split("@")[1].split(",")[0].replace("_", "__").replace(".", "_")
        return \
f"""
/label_export_{export_name} /label_import_{import_name}
Node.(
    NodeType.Delta |
    Read.Label(0){{label_write_{import_name}}} |
    Import.Label(0){{label_import_{import_name}}} |
    Body.Region(0).Node.(
            NodeType.Simple |
            Body.Literal |
            Read.( Const(0,{type_no}) | Label(0){{label_import_{import_name}}} ) |
            Write.(Label(0){{label_export_{export_name}}}) |
            Extra.DataTypes.({transform_type(var_type)}) ) |
    Extra.(
        DataTypes.({transform_type(var_type)}) |
        Options.({join_or_1(" | ",options)})    
    ) |
    Export.Label(0){{label_export_{export_name}}} |
    Write.Label(0){{label_write_{export_name}}}
)
""",  f"label_write_{export_name}"    

    else:
        return \
f"""
/label_export_{export_name}
Node.(
    NodeType.Delta |
    Read.1 |
    Import.1 |
    Body.Region(0).Node.(
            NodeType.Simple |
            Body.Literal |
            Read.Const(0,{type_no}) |
            Write.(Label(0){{label_export_{export_name}}}) |
            Extra.DataTypes.({transform_type(var_type)}) 
            ) |
    Extra.(
        DataTypes.({transform_type(var_type)}) |
        Options.({join_or_1(" | ",options)})    
    ) |
    Export.Label(0){{label_export_{export_name}}} |
    Write.Label(0){{label_write_{export_name}}}
)
""", f"label_write_{export_name}"
    


    # instruction_info = {}
    # instruction_info["opcode"] = ""
    # instruction_info["write"] = []
    # instruction_info["read"] = [ ]
    # instruction_info["type"] = [  ]
    # instruction_info["options"] = []


def translate_instruction_getelementptr(instruction:ValueRef):
    instruction_s = str(instruction)
    instruction_parts = instruction_s.split(",")
    closures = []
    instruction_info = {}
    instruction_info["opcode"] = "Getelementptr"
    address_write, closure = create_address(instruction_parts[0].split()[0])
    closures += [closure]
    instruction_info["write"] = [address_write]
    address_adr, closure = create_address(instruction_parts[1].split()[1], 1)
    closures += [closure]
    address_ind, closure = create_address(instruction_parts[2].split()[1], 2)
    closures += [closure]
    instruction_info["read"] = [ address_adr  , address_ind ]
    instruction_info["type"] = [ transform_type(instruction.type), \
        transform_type(instruction_parts[1].split()[0], 1) ,
        transform_type(instruction_parts[2].split()[0], 2)]
    
    if instruction_parts[0].split()[-2] != instruction.opcode:
        instruction_info["options"] = [transform_option(instruction_parts[0].split()[-2] )]
    else:
        instruction_info["options"] = []
    return instruction_info, closures


def translate_instruction_alloca(instruction):
    instruction = instruction.split()
    instruction_info = {}
    instruction_info["opcode"] = "Alloca"
    write_address, closure = create_address(instruction[0])
    instruction_info["write"] = [write_address]
    instruction_info["read"] = [ ]
    instruction_info["type"] = [ transform_type(instruction[3][:-1])  ]
    instruction_info["options"] = []
    return instruction_info, [closure], instruction[0][1:]

def translate_instruction_bitcast(instruction):
    instruction = instruction.split()
    instruction_info = {}
    instruction_info["opcode"] = "Bitcast"
    closures = []
    write_address, closure = create_address(instruction[0])
    closures += [closure]
    instruction_info["write"] = [write_address]
    read_address, closure = create_address(instruction[4])
    closures += [closure]
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
    return instruction_info, [closure]


def translate_instruction_icmp(instruction):
    instruction = instruction.split()
    instruction_info = {}
    instruction_info["opcode"] = "Icmp"
    closures = []
    write_address, closure = create_address(instruction[0])
    closures += [closure]
    instruction_info["write"] = [write_address]
    read_address1, closure = create_address(instruction[-2], 1)
    closures += [closure]
    read_address2, closure = create_address(instruction[-1], 2)
    closures += [closure]
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
        closures = []
        read_address, closure = create_address(instruction[2])
        closures += [closure]
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
    closures = []
    write_addres, closure = create_address(instruction[0])
    closures += [closure]
    instruction_info["write"] = [ write_addres  ]
    read_address, closure = create_address(instruction[-3])
    closures += [closure]
    instruction_info["read"] = [ read_address ]
    instruction_info["type"] = [ transform_type(instruction[3][:-1], 1), transform_type(instruction[4], 2) ]
    instruction_info["options"] = []

    label = False
    if instruction[-3][0] == "@":
        label = True

    return instruction_info, closures, instruction[-3][1:-1].replace("_","__").replace(".","_"), label

def translate_instruction_store(instruction):
    instruction = instruction.split()
    instruction_info = {}
    instruction_info["opcode"] = "Store"
    closures = []
    write_addres, closure = create_address(instruction[-3]) 
    closures += [closure]
    instruction_info["write"] = [ write_addres ]
    read_addres, closure = create_address(instruction[2])
    closures += [closure]
    instruction_info["read"] = [ read_addres ]
    instruction_info["type"] = [ transform_type(instruction[1], 1), transform_type(instruction[3], 2)]
    instruction_info["options"] = []

    label = False
    if instruction[-3][0] == "@":
        label = True

    return instruction_info, closures, instruction[-3][1:-1].replace("_","__").replace(".","_"), label

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
    closures = []
    closures += [closure]
    instruction_info["write"] = [ write_address ]
    read_address1, closure = create_address(instruction[-2], 1)
    closures += [closure]
    read_address2, closure = create_address(instruction[-1], 2)
    closures+= [closure]
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
    if type(type_string) != str:
        type_string = str(type_string)
    if type_string in strings_dict:
        type_no = strings_dict[type_string]
    else:
        type_no = len(strings_dict)
        strings_dict[type_string] = type_no

    return f"DataType({type_order},{type_no})"

def transform_option(option_string):
    if type(option_string) != str:
        option_string = str(option_string)

    if option_string in strings_dict:
        type_no = strings_dict[option_string]
    else:
        type_no = len(strings_dict)
        strings_dict[option_string] = type_no
    
    return f"Option({type_no})"

def transform_alignment(alignment_string):
    if type(alignment_string) != str:
        alignment_string = str(alignment_string)
        
    if alignment_string in strings_dict:
        type_no = strings_dict[alignment_string]
    else:
        type_no = len(strings_dict)
        strings_dict[alignment_string] = type_no
    
    return f"Alignment({type_no})"

def create_address(number_string, order=-1):
    return_string = ""
    if number_string[0] == "@":
        if number_string[-1] == ",":
            number_string = number_string[:-1]
        label = "label_" + number_string[1:].replace("_", "__").replace(".", "_")
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
    