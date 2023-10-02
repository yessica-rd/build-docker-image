
from sage.rings.integer_ring import ZZ


def generate_bitmask(n):
    """
    Return an `n`-bits integer where every bit is set to 1.

    INPUT:

    - ``n`` -- **integer**; a positive integer.

    EXAMPLES::

        sage: from claasp.utils.integer import generate_bitmask
        sage: bin(generate_bitmask(4))
        '0b1111'
        sage: hex(generate_bitmask(32))
        '0xffffffff'
    """
    return ((1 << (n - 1)) - 1) | (1 << (n - 1)) & 0xFFFFFFFF


def to_binary(x, n):
    """
    Return the `n`-bits binary form of `x` in bitwise little-endian ordering.

    INPUT:

    - ``x`` -- **integer**
    - ``n`` -- **integer**

    EXAMPLES::

        sage: from claasp.utils.integer import to_binary
        sage: to_binary(0x67452301, 32)
        [1, 0, 0, 0, 0, 0, 0, 0, 1, 1, 0, 0, 0, 1, 0, 0, 1, 0, 1, 0, 0, 0, 1, 0, 1, 1, 1, 0, 0, 1, 1, 0]
    """
    return ZZ(x).digits(base=2, padto=n)