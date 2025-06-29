import pytest

from tests.evm_backends.base_env import _compile
from vyper.exceptions import StackTooDeep
from vyper.utils import method_id


def test_init_argument_test(get_contract):
    init_argument_test = """
moose: int128

@deploy
def __init__(_moose: int128):
    self.moose = _moose

@external
def returnMoose() -> int128:
    return self.moose
    """

    c = get_contract(init_argument_test, *[5])
    assert c.returnMoose() == 5
    print("Passed init argument test")


def test_constructor_mapping(get_contract):
    contract = """
foo: HashMap[bytes4, bool]

X: constant(bytes4) = 0x01ffc9a7

@deploy
def __init__():
    self.foo[X] = True

@external
@view
def check_foo(a: bytes4) -> bool:
    return self.foo[a]
    """

    c = get_contract(contract)
    assert c.check_foo("0x01ffc9a7") is True


def test_constructor_advanced_code(get_contract):
    constructor_advanced_code = """
twox: int128

@deploy
def __init__(x: int128):
    self.twox = x * 2

@external
def get_twox() -> int128:
    return self.twox
    """
    c = get_contract(constructor_advanced_code, *[5])
    assert c.get_twox() == 10


def test_constructor_advanced_code2(get_contract):
    constructor_advanced_code2 = """
comb: uint256

@deploy
def __init__(x: uint256[2], y: Bytes[3], z: uint256):
    self.comb = x[0] * 1000 + x[1] * 100 + len(y) * 10 + z

@external
def get_comb() -> uint256:
    return self.comb
    """
    c = get_contract(constructor_advanced_code2, *[[5, 7], b"dog", 8])
    assert c.get_comb() == 5738
    print("Passed advanced init argument tests")


def test_large_input_code(env, get_contract, tx_failed):
    large_input_code = """
@external
def foo(x: int128) -> int128:
    return 3
    """

    c = get_contract(large_input_code)
    signature = "(int128)"
    method = method_id(f"foo{signature}")

    env.message_call(c.address, data=method + (1274124).to_bytes(32, "big"))
    env.message_call(c.address, data=method + (2**120).to_bytes(32, "big"))

    with tx_failed():
        env.message_call(c.address, data=method + (2**130).to_bytes(32, "big"))


def test_large_input_code_2(env, get_contract, tx_failed, output_formats):
    code = """
@deploy
def __init__(x: int128):
    y: int128 = x

@external
def foo() -> int128:
    return 5
    """

    _, bytecode = _compile(code, output_formats)
    ctor_args = (2**127 - 1).to_bytes(32, "big")
    env._deploy(bytecode + ctor_args, value=0)

    with tx_failed():
        env._deploy(bytecode + (2**127).to_bytes(32, "big"), value=0)


def test_initialise_array_with_constant_key(get_contract):
    contract = """
X: constant(uint256) = 4

foo: int16[X]

@deploy
def __init__():
    self.foo[X-1] = -2

@external
@view
def check_foo(a: uint256) -> int16:
    return self.foo[a]
    """

    c = get_contract(contract)
    assert c.check_foo(3) == -2


def test_initialise_dynarray_with_constant_key(get_contract):
    contract = """
X: constant(int16) = 4

foo: DynArray[int16, X]

@deploy
def __init__():
    self.foo = [X - 3, X - 4, X - 5, X - 6]

@external
@view
def check_foo(a: uint64) -> int16:
    return self.foo[a]
    """

    c = get_contract(contract)
    assert c.check_foo(3) == -2


def test_nested_dynamic_array_constructor_arg(env, get_contract):
    code = """
foo: uint256

@deploy
def __init__(x: DynArray[DynArray[uint256, 3], 3]):
    self.foo = x[0][2] + x[1][1] + x[2][0]

@external
def get_foo() -> uint256:
    return self.foo
    """
    c = get_contract(code, *[[[3, 5, 7], [11, 13, 17], [19, 23, 29]]])
    assert c.get_foo() == 39


def test_nested_dynamic_array_constructor_arg_2(env, get_contract):
    code = """
foo: int128

@deploy
def __init__(x: DynArray[DynArray[DynArray[int128, 3], 3], 3]):
    self.foo = x[0][1][2] * x[1][1][1] * x[2][1][0] - x[0][0][0] - x[1][1][1] - x[2][2][2]

@external
def get_foo() -> int128:
    return self.foo
    """
    c = get_contract(
        code,
        *[
            [
                [[3, 5, 7], [11, 13, 17], [19, 23, 29]],
                [[-3, -5, -7], [-11, -13, -17], [-19, -23, -29]],
                [[-31, -37, -41], [-43, -47, -53], [-59, -61, -67]],
            ]
        ],
    )
    assert c.get_foo() == 9580


def test_initialise_nested_dynamic_array(env, get_contract):
    code = """
foo: DynArray[DynArray[uint256, 3], 3]

@deploy
def __init__(x: uint256, y: uint256, z: uint256):
    self.foo = [
        [x, y, z],
        [x * 1000 + y, y * 1000 + z, z * 1000 + x],
        [z * 2, y * 3, x * 4],
    ]

@external
def get_foo() -> DynArray[DynArray[uint256, 3], 3]:
    return self.foo
    """
    c = get_contract(code, *[37, 41, 73])
    assert c.get_foo() == [[37, 41, 73], [37041, 41073, 73037], [146, 123, 148]]


@pytest.mark.venom_xfail(raises=StackTooDeep, reason="stack scheduler regression")
def test_initialise_nested_dynamic_array_2(env, get_contract):
    code = """
foo: DynArray[DynArray[DynArray[int128, 3], 3], 3]

@deploy
def __init__(x: int128, y: int128, z: int128):
    self.foo = [
        [[x, y, z], [y, z, x], [z, y, x]],
        [
            [x * 1000 + y, y * 1000 + z, z * 1000 + x],
            [- (x * 1000 + y), - (y * 1000 + z), - (z * 1000 + x)],
            [- (x * 1000) + y, - (y * 1000) + z, - (z * 1000) + x],
        ],
        [
            [z * 2, y * 3, x * 4],
            [z * (-2), y * (-3), x * (-4)],
            [z * (-y), y * (-x), x * (-z)],
        ],
    ]

@external
def get_foo() -> DynArray[DynArray[DynArray[int128, 3], 3], 3]:
    return self.foo
    """
    c = get_contract(code, *[37, 41, 73])
    assert c.get_foo() == [
        [[37, 41, 73], [41, 73, 37], [73, 41, 37]],
        [[37041, 41073, 73037], [-37041, -41073, -73037], [-36959, -40927, -72963]],
        [[146, 123, 148], [-146, -123, -148], [-2993, -1517, -2701]],
    ]
