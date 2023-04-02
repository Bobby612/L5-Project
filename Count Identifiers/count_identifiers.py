import sys

def main():
    no_ident = 0
    no_lines = 0
    for line in sys.stdin:
        line = line.lower()
        in_ident = False
        is_line = False
        for c in line:
            if not c.isspace() and not is_line:
                is_line = True
                no_lines += 1

            if in_ident:
                if c not in "abcdefghijklmnopqrstuvwxyz_1234567890":
                    in_ident = False
            else:
                if c in "abcdefghijklmnopqrstuvwxyz_":
                    in_ident = True
                    no_ident += 1

    print(f"Identifiers: {no_ident} \nLines: {no_lines} \n")

                

            

if __name__ == "__main__":
    main()