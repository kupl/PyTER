from pyannotate_runtime import collect_types

def hoo(x) :
    return 3

collect_types.init_types_collection()
try :
    with collect_types.collect() :
        def foo() :
            def tmp(x) :
                if x > 1 :
                    return False
                return True
            a = 3
            b = "bb"
            c = tmp(\
                1)
            print(c)

            class MyType() :
                tt = 3
                def __init__(self) :
                    self.a = 1
                    self.b = 2

                def foo(self) :
                    #a = 1 + "b"
                    d = self.a + self.b
                    return d

                def goo(self) :
                    x = "aa"
                    return x

            a = MyType()

            x = a.foo()
            y = 4
            z = x+y

            k = "asdf"

            aa = k + a.tt
            #try :
            #    1 + "aa"
            #except :
            #    pass

            def tmp2(x) :
                if isinstance(x, MyType) :
                    return True
                return False

            tmp2(1)
            return False
        #z = hoo(2)
        d = foo()
finally :
    _fail_args, func = collect_types.my_stats()

    #print(collect_types.dumps_stats())

    print(_fail_args)
    #print(func)