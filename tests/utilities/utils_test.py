import pytest

from utilities.utils import *


def test_get_hash():
    test_string = "ThisIsATestString"
    hashed = hashlib.new('sha256')
    hashed.update(test_string.encode())
    expected = hashed.hexdigest()
    assert get_hash(test_string) == expected


"""
    KiB_512 = 19
    MiB_1 = 20
    MiB_2 = 21
    MiB_4 = 22
    MiB_8 = 23
    MiB_16 = 24
    MiB_32 = 25
"""
@pytest.mark.parametrize(
    ('input', 'expected'),
    (
        (1073741824, 19), # 1 GB => KiB_512
        (2147483648, 20), # 2 GB => MiB_1
        (3221225472, 21), # 3 GB => MiB_2
        (5368709120, 22), # 5 GB => MiB_4
        (7516192768, 22), # 7 GB => MiB_4
        (10737418240, 23), # 10 GB => MiB_8
        (16106127360, 23), # 15 GB => MiB_8
        (21474836480, 24), # 20 GB => MiB_16
        (32212254720, 24), # 30 GB => MiB_16
        (42949672960, 24), # 40 GB => MiB_16
        (53687091200, 24), # 50 GB => MiB_16
        (64424509440, 24), # 60 GB => MiB_16
        (75161927680, 24), # 70 GB => MiB_16
        (85899345920, 24), # 80 GB => MiB_16
        (96636764160, 24), # 90 GB => MiB_16
        (107374182400, 24), # 100 GB => MiB_16
        (214748364800, 24), # 100 GB => MiB_16
    )
)
def test_get_piece_size_for_mktorrent(input, expected):
    assert get_piece_size_for_mktorrent(input) == expected


"""
    MiB_1 = 1048576
    MiB_2 = 2097152
    Mib_4 = 4194304
    Mib_8 = 8388608
    Mib_16 = 16777216
"""
@pytest.mark.parametrize(
    ('input', 'expected'),
    (
        # pytest.param(1, 1, id='test name')
        (1073741824, 1048576), # 1 GB => MiB_1
        (2147483648, 2097152), # 2 GB => MiB_2
        (3221225472, 4194304), # 3 GB => MiB_4
        (5368709120, 4194304), # 5 GB => MiB_4
        (7516192768, 4194304), # 7 GB => MiB_4
        (10737418240, 8388608), # 10 GB => MiB_8
        (16106127360, 8388608), # 15 GB => MiB_8
        (21474836480, 16777216), # 20 GB => MiB_16
        (32212254720, 16777216), # 30 GB => MiB_16
        (42949672960, 16777216), # 40 GB => MiB_16
        (53687091200, 16777216), # 50 GB => MiB_16
        (64424509440, 16777216), # 60 GB => MiB_16
        (75161927680, 16777216), # 70 GB => MiB_16
        (85899345920, 16777216), # 80 GB => MiB_16
        (96636764160, 16777216), # 90 GB => MiB_16
        (107374182400, 16777216), # 100 GB => MiB_16
        (214748364800, 16777216), # 100 GB => MiB_16
    )
)
def test_calculate_piece_size(input, expected):
    assert calculate_piece_size(input) == expected # 1 GB => 1 MiB


@pytest.mark.parametrize(
    ("input", "expected"),
    (
        pytest.param([None], False, id="no_type_provided"),
        pytest.param(["tv"], True, id="tv_type_provided"),
        pytest.param(["movie"], True, id="movie_type_provided"),
        pytest.param(["hello"], False, id="invalid_type_provided"),
        pytest.param(None, False, id="no_inputs"),
    )
)
def test_has_user_provided_type(input, expected):
    assert has_user_provided_type(input) == expected