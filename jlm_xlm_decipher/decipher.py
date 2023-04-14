import sys
import xmltodict

def main(xml_file):
    with open(xml_file, "rb") as f:
        rvsdg = xmltodict.parse(f, force_list={'region', 'node'})

    s, n = traverse(rvsdg["rvsdg"]["region"][0]["node"][0])
    print(s)
    print(n)

    


def traverse(node, indent=""):
    new_indent = "    " + indent
    if "region" in node:
        string = indent + node["@type"] + "\n"
        n = 0
        for region in node["region"]:
            string += indent + "region\n"
            for node in region["node"]:
                s, n2 = traverse(node, new_indent)
                string += s
                n += n2
            string += indent + f"end_region {n}\n"
        return string, n+1
    else:
        if node["@name"] in random_nodes:
            return "", 0
        else:
            return indent + node["@name"] + "\n", 1


random_nodes = ["BITS32(1)", "MemStateMerge", "BITS32(0)", "undef", "BITSLT32", "CTL(0)", "BITS64(0)", "CTL(1)"  ]


if __name__ == "__main__":
    if (len(sys.argv) > 1):
        main(sys.argv[1])
