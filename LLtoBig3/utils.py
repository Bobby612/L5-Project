import global_vars

"""

Author: Borislav Kratchanov
Copyright: 

"""

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

    if number_string in global_vars.strings_dict:
        type_no = global_vars.strings_dict[number_string]
    else:
        type_no = len(global_vars.strings_dict)
        global_vars.strings_dict[number_string] = type_no
    
    dedge = f"Dedge{{constant_{len(global_vars.constant_blocks)}}}.Loc{{adr_{order}}}"
    closure = f" /constant_{len(global_vars.constant_blocks)}"

    global_vars.constant_blocks += [
f"""
/adr_0
Node.(
    NodeType.Simple |
    Body.Literal |
    Read.1 |
    Write.Dedge{{constant_{len(global_vars.constant_blocks)}}}.Loc{{adr_0}} |
    Extra.DataTypes.(Loc1{{adr_0}}.DataType(0,-1) | Loc1{{adr_0}}.Const({type_no}) )
)
"""
    ]
    
    return dedge, closure


def transform_type(type_string, type_order=0):
    if type(type_string) != str:
        type_string = str(type_string)
    if type_string in global_vars.strings_dict:
        type_no = global_vars.strings_dict[type_string]
    else:
        type_no = len(global_vars.strings_dict)
        global_vars.strings_dict[type_string] = type_no

    if type(type_order) == str:
        return f"Loc1{{adr_{type_order}}}.DataType(-1,{type_no})"

    return f"Loc1{{adr_{type_order}}}.DataType({type_order},{type_no})"

def transform_option(option_string):
    if type(option_string) != str:
        option_string = str(option_string)

    if option_string in global_vars.strings_dict:
        type_no = global_vars.strings_dict[option_string]
    else:
        type_no = len(global_vars.strings_dict)
        global_vars.strings_dict[option_string] = type_no
    
    return f"Option({type_no})"


def create_address2(address):
    if address[-1] not in "1234567890":
        address = address[:-1]
    return create_address("%" + address,int(address))[0]


def create_label2(label):
    return f"Dedge{{label_{label[0]}}}.Loc{{flabel_{label[1]}}}"


def transform_alignment(alignment_string):
    if type(alignment_string) != str:
        alignment_string = str(alignment_string)
        
    if alignment_string in global_vars.strings_dict:
        type_no = global_vars.strings_dict[alignment_string]
    else:
        type_no = len(global_vars.strings_dict)
        global_vars.strings_dict[alignment_string] = type_no
    
    return f"Alignment({type_no})"


def join_or_1(join_string, join_list):
    ret = join_string.join(join_list)
    if not ret:
        return "1"
    else:
        return ret


def transform_type3(i):
    type_string = i[1]
    if type(type_string) != str:
        type_string = str(type_string)
    if type_string in global_vars.strings_dict:
        type_no = global_vars.strings_dict[type_string]
    else:
        type_no = len(global_vars.strings_dict)
        global_vars.strings_dict[type_string] = type_no
    return f"Loc1{{olabel_{i[0]}}}.DataType({i[0]},{type_no})"

def create_label3(label):
    return f"Dedge{{{label[1]}}}.Loc{{olabel_{label[0]}}}"