def func_1(apple, my_list):
    if apple<10:
        # Do something 
        my_list.append(apple)
    return my_list[1:]
def func_2(spongebob, squarepants):
    """A less messy function"""
    for char in spongebob:
        if char in squarepants:
            return char
    unused=1
    return None
