from utilities.utils import *

def test_get_hash():
    test_string = "ThisIsATestString"
    hashed = hashlib.new('sha256')
    hashed.update(test_string.encode())
    expected = hashed.hexdigest()
    assert get_hash(test_string) == expected