import  saltools.web    as  sltw

def test_g_xpath(
    ):
    source_A  = '<p>p1</p><p>p2</p>'
    assert sltw.g_xpath(source_A, '//text()') == ['p1', 'p2']