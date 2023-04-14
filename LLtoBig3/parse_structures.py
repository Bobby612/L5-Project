from llvmlite.binding.value import ValueRef

import global_vars
from utils import *
from parse_instructions import *


"""

Author: Borislav Kratchanov, b.k.kratchanov@gmail.com

Copying: Check License file in top level of GitHub repository for information on redistribution and use

Parse the different structures

"""


def parse_function(function: ValueRef):
    func_type = function.type
    export_name = str(function.name).replace("_", "__").replace(".", "_")
    export = []
    closed_links = []
    
    if not str(func_type)[:4] == "void":
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
        closed_links += [ f"adr_{a}"]


    return \
f"""
{" ".join( list(map(lambda x: "/" + x, closed_links)))} /flabel_0 /adr_s_met_state
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
    global_vars.constant_blocks = []

    block_body = []
    import_address = set()
    import_labels = set()
    export_address = set()
    export_labels = set()

    closures = set()
    e = str(block).split("\n")[1].split(":")[0]
    if e[0] not in "1234567890":
        e = "0"
    entrance_register = "cfg_" + e

    for instruction in block.instructions:
        match instruction.opcode:
            case "add" | "sub" | "mul" | "shl" | "srem" | "urem" | "sdiv" | "fadd" | "fsub" | \
                    "fmul" | "fdiv" | "frem":
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
                instruction_node, closure, store_address, is_label = translate_instruction_store(instruction, state, state_dict)
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
                if str(instruction).split()[1] == "void":
                    continue
                instruction_node, closure = translate_instruction_ret(str(instruction))
                closures.update(closure)
                block_body += [ output_bigraph_simple_node(instruction_node) ]
                ret_label = True

            case "bitcast" | "sitofp" :
                instruction_node, closure = translate_instruction_instr_to(str(instruction))
                closures.update(closure)
                block_body += [ output_bigraph_simple_node(instruction_node) ]
            case "alloca":
                instruction_node, closure, function_address = translate_instruction_alloca(str(instruction), state_dict)
                closures.update(closure)
                no_import_state += closure
                block_body += [ output_bigraph_simple_node(instruction_node) ]
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


    block_body = global_vars.constant_blocks + block_body

    closures.update(map(lambda x : " /" + x,list(state_dict.values())))

    import_address = list(import_address & set(function_addresses))
    import_address = list(map(create_address2, import_address))
    import_labels = list(import_labels)
    import_labels = list(map(create_label2, import_labels))

    export_address = list(export_address)
    export_address = list(map(create_address2, export_address))

    if ret_label:
        ret_label = ["Dedge{return_address}.Loc{adr_return}"]
    else:
        ret_label = []

    state_import = [] ##  f"state_{closure[2:]}"
    state_export = []

    for k,v in state_dict.items():
        closures.add(f" /state_{k[2:]}")
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
    Export.({join_or_1(" | ", ret_label + state_export)})

)
""", labels, function_addresses, entrance_register


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

    if literal in global_vars.strings_dict:
        type_no = global_vars.strings_dict[literal]
    else:
        type_no = len(global_vars.strings_dict)
        global_vars.strings_dict[literal] = type_no
    
    if var_type[-2] == "*":
        
        import_name = literal.split("@")[1].split(",")[0].replace("_", "__").replace(".", "_")
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