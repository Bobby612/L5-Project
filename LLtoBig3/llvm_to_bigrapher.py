import llvmlite.binding as llvm
from llvmlite.ir.instructions import *
from llvmlite.binding.value import ValueRef
import json
import sys, os

strings_dict = {}

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
        json.dump(strings_dict, f)

    
    with open(new_file_name + ".big", "w") as f:
        f.writelines(omega)

    print("ok")


def transform_type3(i):
    type_string = i[1]
    if type(type_string) != str:
        type_string = str(type_string)
    if type_string in strings_dict:
        type_no = strings_dict[type_string]
    else:
        type_no = len(strings_dict)
        strings_dict[type_string] = type_no
    return f"Loc1{{olabel_{i[0]}}}.DataType({i[0]},{type_no})"

def create_label3(label):
    return f"Dedge{{{label[1]}}}.Loc{{olabel_{label[0]}}}"

def parse_function(function: ValueRef):
    func_type = function.type
    export_name = function.name
    export = []
    closed_links = []
    if not str(func_type) == "void":
        export += ["Dedge{return_address}.Loc{adr_return}"]
        closed_links += ["return_address", "adr_return"]
    
    blocks = []
    labels = []
    addresses = []
    label_state:set[int] = set()
    label_state_connect = []

    read_labels = []
    import_labels_adr = []
    types = [transform_type(func_type, "return")]

    for i, arg in enumerate(function.arguments):
        arg = str(arg).split()
        types += [transform_type(arg[0], i)]
        address, closure = create_address(arg[1], i)
        import_labels_adr += [address]
        closed_links += [closure[2:], f"adr_{i}" ]
        addresses += [str(i)]


    for b in function.blocks:
        block, labels, addresses, cfg_node_entrance = parse_block(b, labels, addresses, label_state)
        blocks += [block]
        closed_links += [cfg_node_entrance]
    
    # labels = list(map(lambda x : x.replace("_","__").replace(".","_"), labels))
    import_function_itself = ""
    if not blocks:
        read_labels  += [f"Dedge{{label_read_function_{export_name}}}.Loc{{flabel__1}}"]
        import_function_itself = f"label_read_function_{export_name}"
        closed_links += ["flabel__1"]

    for i, l in enumerate(labels):
        read_labels += [f"Dedge{{label_write_{l}}}.Loc{{flabel_{i}}}"]
        import_labels_adr += [f"Dedge{{label_{l}}}.Loc{{flabel_{i}}}"]
        closed_links += [ f"label_{l}", f"flabel_{i}"]

    for i in label_state:
        import_labels_adr += [f"Dedge{{label_s_{i}}}.Loc{{flabel_s_{i}}}"]
        closed_links += [f"label_s_{i}", f"flabel_s_{i}"]
        label_state_connect += [f"Loc1{{flabel_{i}}}.Loc1{{flabel_s_{i}}}.State"]

    for a in addresses:
        # import_labels_adr += [f"Dedge{{label_{a}}}.Loc{{adr_{a}}}"]

        closed_links += [ f"adr_{a}"]


    return \
f"""
{" ".join( list(map(lambda x: "/" + x, closed_links)))} /flabel_0
Node.(
    NodeType.Lambda |
    Read.({join_or_1(" | ", read_labels)}) |
    Import.({join_or_1(" | ", import_labels_adr)}) |
    Body.Region(0).(
        {join_or_1(''' |
        ''', blocks)}
    ) | /e
    Extra.DataTypes.( {join_or_1(" | ", types + label_state_connect + ["Loc1{e}.Loc1{adr_s_met_state}.State"])} 
    ) |
    Export.({join_or_1(" | ", export)}) |
    Write.Dedge{{label_write_{export_name}}}.Loc{{flabel_0}}
)
""", f"label_write_{export_name}", import_function_itself

def parse_block(block:ValueRef, labels:list, function_addresses:list, label_state:set[int]):
    entrance_register = ""
    exit_register = ""
    state = 0
    state_dict = {}
    no_import_state = []
    ret_label = False

    # function_addresses = []
    

    block_body = []
    import_address = set()
    import_labels = set()
    export_address = set()
    export_labels = set()

    closures = set()

    for instruction in block.instructions:
        if instruction.opcode == "store":
            continue
        if instruction.opcode == "br":
            e = int(str(instruction).split()[2][1:])
        else:
            e = int(str(instruction).split()[0][1:])
        entrance_register = "cfg_" + str(e-1)
        break

    for instruction in block.instructions:
        match instruction.opcode:
            case "add" | "sub" | "mul" | "shl" | "srem" | "urem" | "sdiv":
                instruction_node, closure = translate_instruction_quad(str(instruction))
                closures.update(closure)
                block_body += [ output_bigraph_simple_node(instruction_node) ]
            case "load":
                instruction_node, closure, load_address, is_label = translate_instruction_load(str(instruction), state, state_dict)
                closures.update(closure)
                block_body += [ output_bigraph_simple_node(instruction_node) ]
                if is_label:
                    export_labels.add(closure[1])
                    if load_address in labels:
                        import_labels.add((load_address, labels.index(load_address)))
                    else:
                        labels.append(load_address)
                        import_labels.add((load_address, labels.index(load_address)))
                else:
                    import_address.add(load_address)

            case "store":
                instruction_node, closure, store_address, is_label = translate_instruction_store(str(instruction), state, state_dict)
                for ra in instruction_node["read_addresses"]:
                    ## fixes a specific case where the function argument is stored
                    if ra[0] == "%":
                        import_address.add(ra[1:])
                closures.update(closure)
                block_body += [ output_bigraph_simple_node(instruction_node) ]
                if is_label:
                    if store_address in labels:
                        export_labels.add(closure[1])
                    else:
                        labels.append(store_address)
                        export_labels.add(closure[1])
                else:
                    export_address.add(store_address)
                    if store_address not in function_addresses:
                        function_addresses.append(store_address)

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
                i = instruction_string.index("@")
                j = instruction_string[i:].index("(") + i
                function_label = instruction_string[i+1:j].replace("_","__").replace(".","_")

                if function_label in labels:
                    import_labels.add((function_label, labels.index(function_label)))
                else:
                    labels.append(function_label)
                    import_labels.add((function_label, labels.index(function_label)))
                    closures.add("/label_" + function_label)
                instruction_node, closure, label = translate_instruction_call_complex(instruction, "@" + function_label, state_dict, instruction_string[i:j])
                
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
                ret_label = True

            case "bitcast":
                instruction_node, closure = translate_instruction_bitcast(str(instruction))
                closures.update(closure)
                block_body += [ output_bigraph_simple_node(instruction_node) ]
            case "alloca":
                instruction_node, closure, function_address = translate_instruction_alloca(str(instruction), state_dict)
                closures.update(closure)
                no_import_state += closure
                block_body += [ output_bigraph_simple_node(instruction_node) ]
                # function_addresses.append(function_address)
            case "getelementptr":
                instruction_node, closure = translate_instruction_getelementptr(instruction)
                closures.update(closure)
                block_body += [ output_bigraph_simple_node(instruction_node)]
            case "sext":
                instruction_node, closure = translate_instruction_sext(instruction)
                closures.update(closure)
                block_body += [ output_bigraph_simple_node(instruction_node)]

            case other:
                print(f"Unknown instruction {other}")

    # block_body += [f"""    Multiplex.(
    #     Read.({join_or_1(" | ", [f"Dedge{{state_{state}}}.State"] + list(map(lambda x: f"Dedge{{{state_dict[x]}}}.State", state_dict.keys() )))}) |
    #     Write.Dedge{{state_{state+1}}}.State
    # )"""]

    closures.update(map(lambda x : " /" + x,list(state_dict.values())))

    # print(import_address, function_addresses)
    import_address = list(import_address & set(function_addresses))
    import_address = list(map(create_address2, import_address))
    import_labels = list(import_labels)
    import_labels = list(map(create_label2, import_labels))

    export_address = list(export_address)
    export_address = list(map(create_address2, export_address))
    # export_labels = list(export_labels)
    # export_labels = list(map(create_label2, export_labels))

    if ret_label:
        ret_label = ["Dedge{return_address}.Loc{adr_return}"]
    else:
        ret_label = []

    state_import = [] ##  f"state_{closure[2:]}"
    state_export = []

    for k,v in state_dict.items():
        closures.add(f" /state_{k[2:]}")
        # print(k, str(export_labels) )
        if k in export_labels:
            
            i = labels.index(k[8:])
            loc = f"flabel_s_{i}"
            label_state.add(i)
        else:
            loc = f"s_{k[2:]}"
            if loc not in function_addresses:
                    function_addresses += [loc]
            loc = f"adr_{loc}"
        
        if k in no_import_state:
            state_export += [f"Dedge{{{v}}}.Loc{{{loc}}}"]
        else:
            if v == f"state_{k[2:]}":
                state_import += [f"Dedge{{{v}}}.Loc{{{loc}}}"]
            else:
                state_import += [f"Dedge{{state_{k[2:]}}}.Loc{{{loc}}}"]
                state_export += [f"Dedge{{{v}}}.Loc{{{loc}}}"]

    return\
f"""
{" ".join(list(closures))}
Block.(
    Interface.(
        BlockEntry{{{entrance_register}}} 
        {exit_register}
    ) |
    Import.({join_or_1(" | ", import_address + import_labels + state_import)}) |
    Body.Region(0).(
        {join_or_1(''' |
        ''', block_body)}
    ) |
    Export.({join_or_1(" | ", ret_label + state_export + export_address)})

)
""", labels, function_addresses, entrance_register

def create_address2(address):
    if address[-1] not in "1234567890":
        address = address[:-1]
    return create_address("%" + address,int(address))[0]

def create_label2(label):
    return f"Dedge{{label_{label[0]}}}.Loc{{flabel_{label[1]}}}"



def translate_instruction_call_complex(instruction:ValueRef, name:str, state_dict:dict[str,str], name_og):
    instruction_2_split = str(instruction).split(name_og)
    call_info = instruction_2_split[0]
    if " /met_state" not in state_dict:
        in_state =  f"Dedge{{met_state}}.Loc{{adr_s}}"
        state_dict[" /met_state"] = "met_states"
        closures = [" /met_state"]
        out_state = f"Dedge{{{state_dict[' /met_state']}}}.Loc{{adr_s}}"
    else:
        in_state = f"Dedge{{{state_dict[' /met_state']}}}.Loc{{adr_s}}"
        closures = [ " /" + state_dict[" /met_state"]]
        state_dict[" /met_state"] = state_dict[" /met_state"] + "s"
        out_state = f"Dedge{{{state_dict[' /met_state']}}}.Loc{{adr_s}}"

    labels = []
    instruction_info = {}
    instruction_info["in_instruction"] = ["/adr_0", "/adr_1", "/adr_s"]
    instruction_info["opcode"] = "Call"
    instruction_info["write"] = [out_state]

    function_adr, closure = create_address(name, 1)
    closures += [closure]

    
    if "%" in call_info :
        adr, closure = create_address(call_info.split()[0])
        closures += [closure]
        instruction_info["write"] += [ adr ]
        
    
    instruction_info["type"] = ["Loc1{adr_s}.State"]
    instruction_info["read"] = [ in_state, function_adr ]
    j = 2
    gep = False
    gep_expr = ""
    for i in instruction_2_split[1].split():
        if i[0] == "#":
            break
        if i[0] == "@":
            adr, closure = create_address(i,j-1)
            closures += [closure]
            instruction_info["read"] += [ adr ]
            labels += [closure[8:]]
            instruction_info["in_instruction"] += [f"/adr_{j-1}"]
        if j%2 == 0:
            instruction_info["type"] += [transform_type(i,j)]
            j += 1
        else:
            if not gep:
                if i == "getelementptr":
                    gep = True
                    gep_expr += i
                else:
                    adr, closure = create_address(i,j-1)
                    closures += [closure]
                    instruction_info["read"] += [ adr ]
                    instruction_info["in_instruction"] += [f"/adr_{j-1}"]
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
                    instruction_info["read"] += [ f'Loc1{{adr_{j-1}}}.Const({type_no})' ]
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
/label_export_{export_name} /label_import_{import_name} /adr_0
Node.(
    NodeType.Delta |
    Read.Dedge{{label_write_{import_name}}}.Loc{{adr_0}} |
    Import.Dedge{{label_import_{import_name}}}.Loc{{adr_0}} |
    /adr_0
    Body.Region(0).Node.(
            NodeType.Simple |
            Body.Literal |
            Read.(Loc1{{adr_0}}.Const({type_no}) | Dedge{{label_import_{import_name}}}.Loc{{adr_0}} ) |
            Write.(Dedge{{label_export_{export_name}}}.Loc{{adr_0}}) |
            Extra.DataTypes.({transform_type(var_type)}) ) |
    Extra.(
        DataTypes.({transform_type(var_type)}) |
        Options.({join_or_1(" | ",options)})    
    ) |
    Export.Dedge{{label_export_{export_name}}}.Loc{{adr_0}} |
    Write.Dedge{{label_write_{export_name}}}.Loc{{adr_0}}
)
""",  f"label_write_{export_name}"    

    else:
        return \
f"""
/label_export_{export_name} /adr_0
Node.(
    NodeType.Delta |
    Read.1 |
    Import.1 |
    /adr_0 /l
    Body.Region(0).Node.(
            NodeType.Simple |
            Body.Literal |
            Read.Loc1{{l}}.Const({type_no}) |
            Write.(Dedge{{label_export_{export_name}}}.Loc{{adr_0}}) |
            Extra.DataTypes.({transform_type(var_type)}) 
            ) |
    Extra.(
        DataTypes.({transform_type(var_type)}) |
        Options.({join_or_1(" | ",options)})    
    ) |
    Export.Dedge{{label_export_{export_name}}}.Loc{{adr_0}} |
    Write.Dedge{{label_write_{export_name}}}.Loc{{adr_0}}
)
""", f"label_write_{export_name}"
    


    # instruction_info = {}
    # instruction_info["opcode"] = ""
    # instruction_info["write"] = []
    # instruction_info["read"] = [ ]
    # instruction_info["type"] = [  ]
    # instruction_info["options"] = []
    # instruction_info["in_instruction"] = []

def translate_instruction_sext(instruction):
    instruction = str(instruction).split()
    instruction_info = {}
    closures = []
    instruction_info["opcode"] = "Sext"
    address_write, closure = create_address(instruction[0])
    closures += [closure]
    instruction_info["write"] = [address_write]

    address_read, closure = create_address(instruction[4], 1)
    closures += [closure]
    
    instruction_info["read"] = [address_read]
    instruction_info["type"] = [transform_type(instruction[-1]), transform_type(instruction[3], 1)  ]
    instruction_info["options"] = []
    instruction_info["in_instruction"] = ["/adr_0", "/adr_1"]

    return instruction_info, closures


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

    instruction_info["in_instruction"] = ["/adr_0", "/adr_1", "/adr_2"]
    return instruction_info, closures


def translate_instruction_alloca(instruction, state_dict):
    instruction = instruction.split()
    instruction_info = {}
    instruction_info["opcode"] = "Alloca"
    write_address, closure = create_address(instruction[0])
    state_dict[closure] = f"state_{closure[2:]}"
    instruction_info["write"] = [write_address, f"Dedge{{{state_dict[closure]}}}.Loc{{adr_s}}" ]
    instruction_info["read"] = [ ]
    instruction_info["type"] = [ transform_type(instruction[3][:-1]), "Loc1{adr_s}.State"  ]
    instruction_info["options"] = []
    instruction_info["in_instruction"] = ["/adr_0", "/adr_s"]
    return instruction_info, [closure], instruction[0][1:]

def translate_instruction_bitcast(instruction):
    instruction = instruction.split()
    instruction_info = {}
    instruction_info["opcode"] = "Bitcast"
    closures = []
    write_address, closure = create_address(instruction[0])
    closures += [closure]
    instruction_info["write"] = [write_address]
    read_address, closure = create_address(instruction[4], 1)
    closures += [closure]
    instruction_info["read"] = [read_address]
    instruction_info["type"] = [ transform_type(instruction[3], 1), transform_type(instruction[6]) ]
    instruction_info["options"] = []
    instruction_info["in_instruction"] = ["/adr_0", "/adr_1"]
    return instruction_info, closures



def translate_instruction_ret(instruction):
    instruction = instruction.split()
    instruction_info = {}
    instruction_info["opcode"] = "Ret"
    instruction_info["write"] = ["Dedge{return_address}.Loc{adr_0}"]
    read_address, closure = create_address(instruction[2], 1)
    instruction_info["read"] = [ read_address ]
    instruction_info["type"] = [ transform_type(instruction[1], 1)  ]
    instruction_info["options"] = []
    instruction_info["in_instruction"] = ["/adr_1", "/adr_0"]
    return instruction_info, [closure, " /return_address"]


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
    instruction_info["type"] = [ transform_type(instruction[4]), transform_type(instruction[4], 0), transform_type(instruction[4], 1) ]
    instruction_info["options"] = [transform_option(instruction[3])]
    instruction_info["in_instruction"] = ["/adr_0", "/adr_1", "/adr_2"]
    return instruction_info, closures

def translate_instruction_br(instruction):
    instruction = str(instruction)
    instruction = instruction.split()
    if instruction[1] == "i1":
        instruction_info = {}
        instruction_info["opcode"] = "Br"
        instruction_info["write"] = []
        closures = []
        read_address, closure = create_address(instruction[2], 1)
        closures += [closure]
        instruction_info["read"] = [ read_address ]
        instruction_info["type"] = [  ]
        instruction_info["options"] = []
        instruction_info["in_instruction"] = ["/adr_1"]
        return instruction_info, closures, "cfg_" + instruction[4][1:-1], "cfg_" + instruction[6][1:]
    else:
        return "cfg_" + instruction[2][1:]


def translate_instruction_load(instruction, state, state_dict):
    instruction = instruction.split()
    instruction_info = {}
    instruction_info["opcode"] = "Load"
    closures = []
    write_addres, closure = create_address(instruction[0])
    closures += [closure]
    instruction_info["write"] = [ write_addres  ]
    read_address, closure = create_address(instruction[-3], 1)

    if closure in state_dict:
        state_string = f"Dedge{{{state_dict[closure]}}}.Loc{{adr_s}}"
    else:
        state_dict[closure] = f"state_{closure[2:]}"
        state_string = f"Dedge{{state_{closure[2:]}}}.Loc{{adr_s}}"

    closures += [closure]
    instruction_info["read"] = [ read_address, state_string ]
    instruction_info["type"] = [ transform_type(instruction[3][:-1]),
                                 transform_type(instruction[4], 1),
                                 "Loc1{adr_s}.State" ]
    instruction_info["options"] = []

    label = False
    if instruction[-3][0] == "@":
        label = True

    instruction_info["in_instruction"] = ["/adr_0", "/adr_1", "/adr_s"]
    return instruction_info, closures, instruction[-3][1:-1].replace("_","__").replace(".","_"), label, 

def translate_instruction_store(instruction, state, state_dict:dict[str,str]):
    instruction = instruction.split()
    instruction_info = {}
    instruction_info["opcode"] = "Store"
    closures = []
    read_addres, closure = create_address(instruction[2], 1)
    closures += [closure]
    
    write_addres, closure = create_address(instruction[-3])
    # print(closure)
    if closure in state_dict:
        in_state = f"Dedge{{{state_dict[closure]}}}.Loc{{adr_s}}"
        closures += [ " /" + state_dict[closure] ]
        state_dict[closure] += "s"
        out_state = f"Dedge{{{state_dict[closure]}}}.Loc{{adr_s}}"
    else:
        in_state = f"Dedge{{state_{closure[2:]}}}.Loc{{adr_s}}"
        state_dict[closure] = f"state_{closure[2:]}s"
        out_state = f"Dedge{{{state_dict[closure]}}}.Loc{{adr_s}}"
    closures += [closure]
    instruction_info["write"] = [ out_state ]
    
    instruction_info["read"] = [ read_addres, write_addres, in_state ]
    instruction_info["type"] = [ transform_type(instruction[1], 1), 
                                transform_type(instruction[3], 0),
                                "Loc1{adr_s}.State"]
    instruction_info["options"] = []

    label = False
    if instruction[-3][0] == "@":
        label = True

    instruction_info["in_instruction"] = ["/adr_0", "/adr_1", "/adr_s"]
    instruction_info["read_addresses"] = [instruction[-3][:-1].replace("_","__").replace(".","_"), instruction[2][:-1].replace("_","__").replace(".","_") ]
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
    instruction_info["type"] = [ transform_type(instruction[-3]),  transform_type(instruction[-3], 1),  transform_type(instruction[-3], 2)  ]
    if instruction[-4] != instruction[2]:
        instruction_info["options"] = [transform_option(instruction[-4])]
        if instruction[-5] != instruction[2]:
            instruction_info["options"] += [transform_option(instruction[-5])]
    else:
        instruction_info["options"] = []

    instruction_info["in_instruction"] = ["/adr_0", "/adr_1", "/adr_2"]
    return instruction_info, closures
    
def output_bigraph_simple_node(info):
    return\
f"""
{" ".join(info["in_instruction"])}
Node.(
    NodeType.Simple |
    Body.Instruction("{info["opcode"]}") |
    Read.({join_or_1(" | ",info["read"])}) |
    Write.({join_or_1(" | ",info["write"])}) |
    Extra.(
        DataTypes.({join_or_1(" | ",info["type"])}) |
        Options.({join_or_1(" | ",info["options"])})    
    )
)
"""

def transform_type(type_string, type_order=0):
    if type(type_string) != str:
        type_string = str(type_string)
    if type_string in strings_dict:
        type_no = strings_dict[type_string]
    else:
        type_no = len(strings_dict)
        strings_dict[type_string] = type_no

    if type(type_order) == str:
        return f"Loc1{{adr_{type_order}}}.DataType(-1,{type_no})"

    return f"Loc1{{adr_{type_order}}}.DataType({type_order},{type_no})"

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

def create_address(number_string, order=0):
    return_string = ""
    if number_string[0] == "@":
        if number_string[-1] == ",":
            number_string = number_string[:-1]
        label = "label_" + number_string[1:].replace("_", "__").replace(".", "_")
        return f"Dedge{{{label}}}.Loc{{adr_{order}}}", " /" + label   
    
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
        return f"Dedge{{{return_string}}}.Loc{{adr_{order}}}", " /" + return_string

    if not str.isdigit(number_string[-1]):
        number_string = number_string[:-1]
    
    return f"Loc1{{adr_{order}}}.Const({number_string})", ""

def join_or_1(join_string, join_list):
    ret = join_string.join(join_list)
    if not ret:
        return "1"
    else:
        return ret

if __name__ == "__main__":
    if len(sys.argv) == 2:
        main(sys.argv[1])
    else:
        print("No filename provided!")
    