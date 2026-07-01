
from inspect import signature as _mutmut_signature
from typing import Annotated
from typing import Callable
from typing import ClassVar


MutantDict = Annotated[dict[str, Callable], "Mutant"]


def _mutmut_trampoline(orig, mutants, call_args, call_kwargs, self_arg = None):
    """Forward call to original or mutated function, depending on the environment"""
    import os
    mutant_under_test = os.environ['MUTANT_UNDER_TEST']
    if mutant_under_test == 'fail':
        from mutmut.__main__ import MutmutProgrammaticFailException
        raise MutmutProgrammaticFailException('Failed programmatically')      
    elif mutant_under_test == 'stats':
        from mutmut.__main__ import record_trampoline_hit
        record_trampoline_hit(orig.__module__ + '.' + orig.__name__)
        result = orig(*call_args, **call_kwargs)
        return result
    prefix = orig.__module__ + '.' + orig.__name__ + '__mutmut_'
    if not mutant_under_test.startswith(prefix):
        result = orig(*call_args, **call_kwargs)
        return result
    mutant_name = mutant_under_test.rpartition('.')[-1]
    if self_arg is not None:
        # call to a class method where self is not bound
        result = mutants[mutant_name](self_arg, *call_args, **call_kwargs)
    else:
        result = mutants[mutant_name](*call_args, **call_kwargs)
    return result
def x_bitcount__mutmut_orig(n):
    count = 0
    while n:
        n &= n - 1
        count += 1
    return count
def x_bitcount__mutmut_1(n):
    count = None
    while n:
        n &= n - 1
        count += 1
    return count
def x_bitcount__mutmut_2(n):
    count = 1
    while n:
        n &= n - 1
        count += 1
    return count
def x_bitcount__mutmut_3(n):
    count = 0
    while n:
        n = n - 1
        count += 1
    return count
def x_bitcount__mutmut_4(n):
    count = 0
    while n:
        n |= n - 1
        count += 1
    return count
def x_bitcount__mutmut_5(n):
    count = 0
    while n:
        n &= n + 1
        count += 1
    return count
def x_bitcount__mutmut_6(n):
    count = 0
    while n:
        n &= n - 2
        count += 1
    return count
def x_bitcount__mutmut_7(n):
    count = 0
    while n:
        n &= n - 1
        count = 1
    return count
def x_bitcount__mutmut_8(n):
    count = 0
    while n:
        n &= n - 1
        count -= 1
    return count
def x_bitcount__mutmut_9(n):
    count = 0
    while n:
        n &= n - 1
        count += 2
    return count

x_bitcount__mutmut_mutants : ClassVar[MutantDict] = {
'x_bitcount__mutmut_1': x_bitcount__mutmut_1, 
    'x_bitcount__mutmut_2': x_bitcount__mutmut_2, 
    'x_bitcount__mutmut_3': x_bitcount__mutmut_3, 
    'x_bitcount__mutmut_4': x_bitcount__mutmut_4, 
    'x_bitcount__mutmut_5': x_bitcount__mutmut_5, 
    'x_bitcount__mutmut_6': x_bitcount__mutmut_6, 
    'x_bitcount__mutmut_7': x_bitcount__mutmut_7, 
    'x_bitcount__mutmut_8': x_bitcount__mutmut_8, 
    'x_bitcount__mutmut_9': x_bitcount__mutmut_9
}

def bitcount(*args, **kwargs):
    result = _mutmut_trampoline(x_bitcount__mutmut_orig, x_bitcount__mutmut_mutants, args, kwargs)
    return result 

bitcount.__signature__ = _mutmut_signature(x_bitcount__mutmut_orig)
x_bitcount__mutmut_orig.__name__ = 'x_bitcount'
