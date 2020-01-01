import  saltools.misc    as  sltm

def test_join_string_array  (
    ):
    case_A  = [
        ', hello'   ,
        ','         ,
        ' ABC , '   ]
    
    assert sltm.join_string_array(case_A, ', ') == 'hello, ABC'