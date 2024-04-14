def test_func1():
    output = test_func2()
    return output

def test_func2():
    var4 = 5
    return var4

print(test_func1())