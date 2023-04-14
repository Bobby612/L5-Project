from llvmlite.binding.value import ValueRef

from utils import *
import global_vars

"""

Author: Borislav Kratchanov, b.k.kratchanov@gmail.com

Copying: Check License file in top level of GitHub repository for information on redistribution and use

Parse the LLVM instructions into a dictionary.

Instruction info dictionary format:
    instruction_info = {}
    instruction_info["opcode"] = ""
    instruction_info["write"] = []
    instruction_info["read"] = [ ]
    instruction_info["type"] = [ ]
    instruction_info["options"] = []
    instruction_info["in_instruction"] = []

"""

def translate_instruction_call_complex(instruction:ValueRef, name:str, state_dict:dict[str,str], name_og):
    """
    Translate a call instruction that could have a getaddrptr constant as an argument
    """

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
                    if current_string in global_vars.strings_dict:
                        type_no = global_vars.strings_dict[current_string]
                    else:
                        type_no = len(global_vars.strings_dict)
                        global_vars.strings_dict[current_string] = type_no

                    gep = False
                    instruction_info["read"] += [ f'Loc1{{adr_{j-1}}}.Const({type_no})' ]
                    gep_expr = ""
                    j += 1
                else:
                    gep_expr += i


    
    instruction_info["type"] += [ transform_type(instruction.type) ]
    instruction_info["options"] = []

    return instruction_info, closures, labels


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
    """
    Translate a runtime getelementptr instruction
    """
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


def translate_instruction_instr_to(instruction):
    """
    '.. to' instruction
    <result> = sitofp <ty> <value> to <ty2>
    <result> = bitcast <ty> <value> to <ty2>
    """
    part2 = instruction.split("to")[-1:]
    part1 = instruction.split()
    part1 = part1[:3] + [" ".join(part1[3:-1])] + part1[-1:]
    instruction = part1 + part2
    
    instruction_info = {}
    instruction_info["opcode"] = instruction[2].capitalize()
    closures = []
    write_address, closure = create_address(instruction[0])
    closures += [closure]
    instruction_info["write"] = [write_address]
    read_address, closure = create_address(instruction[-3], 1)
    closures += [closure]
    instruction_info["read"] = [read_address]
    instruction_info["type"] = [ transform_type(" ".join(instruction[3:-3]), 1), transform_type(instruction[-1]) ]
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
    instruction = instruction.split(",")
    part1 = instruction[0].split()
    part2 = instruction[1].split()
    part1 = part1[:3] + [" ".join(part1[3:])]
    part2 = [" ".join(part2[:-1])] + part2[-1:]
    instruction = part1 + part2 + instruction[-1:]

    instruction_info = {}
    instruction_info["opcode"] = "Load"
    closures = []
    write_addres, closure = create_address(instruction[0])
    closures += [closure]
    instruction_info["write"] = [ write_addres  ]
    read_address, closure = create_address(instruction[-2], 1)

    if closure in state_dict:
        state_string = f"Dedge{{{state_dict[closure]}}}.Loc{{adr_s}}"
    else:
        state_dict[closure] = f"state_{closure[2:]}"
        state_string = f"Dedge{{state_{closure[2:]}}}.Loc{{adr_s}}"

    closures += [closure]
    instruction_info["read"] = [ read_address, state_string ]
    instruction_info["type"] = [ transform_type(instruction[3]),
                                 transform_type(instruction[4], 1),
                                 "Loc1{adr_s}.State" ]
    instruction_info["options"] = []

    label = False
    if instruction[-2][0] == "@":
        label = True

    instruction_info["in_instruction"] = ["/adr_0", "/adr_1", "/adr_s"]
    return instruction_info, closures, instruction[-2][1:].replace("_","__").replace(".","_"), label, 


def translate_instruction_store(instruction1:ValueRef, state, state_dict:dict[str,str]):
    instr_type = instruction1.type
    instruction = str(instruction1)
    instruction = instruction.split(",")
    part1 = instruction[0].split()
    part2 = instruction[1].split()
    part1 = part1[:1] + [" ".join(part1[1:-1])] + part1[-1:]
    part2 = [" ".join(part2[0:-1])] + part2[-1:]

    instruction = part1 + part2 + [instruction[-1]]

    instruction_info = {}
    instruction_info["opcode"] = "Store"
    closures = []
    read_addres, closure = create_address(instruction[2], 1)
    closures += [closure]
    
    write_addres, closure = create_address(instruction[-2], 2)
    
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
                                transform_type(instruction[3], 2),
                                "Loc1{adr_s}.State"]
    instruction_info["options"] = []

    label = False
    if instruction[-2][0] == "@":
        label = True

    instruction_info["in_instruction"] = ["/adr_2", "/adr_1", "/adr_s"]
    instruction_info["read_addresses"] = [instruction[-2].replace("_","__").replace(".","_"), instruction[2].replace("_","__").replace(".","_") ]
    return instruction_info, closures, instruction[-2][1:].replace("_","__").replace(".","_"), label


def translate_instruction_quad(instruction):
    """
    Translate a typical integer arithmetic instruction with op-code, type, two operands,
    and up to two extra options.

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