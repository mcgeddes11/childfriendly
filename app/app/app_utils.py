def is_integer(input_string):
    try:
        int_out = int(input_string)
        tf = True
    except:
        int_out = None
        tf = False
    return tf, int_out