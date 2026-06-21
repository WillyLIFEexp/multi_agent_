"""Discrete math / statistics helper tools."""
import math
import statistics

from langchain_core.tools import tool


@tool
def square_root(x: float) -> str:
    """Return the square root of a non-negative number."""
    if x < 0:
        return "Error: cannot take square root of a negative number"
    return str(math.sqrt(x))


@tool
def factorial(n: int) -> str:
    """Return n! for a non-negative integer n."""
    if n < 0:
        return "Error: factorial is undefined for negative numbers"
    return str(math.factorial(n))


@tool
def gcd(a: int, b: int) -> str:
    """Return the greatest common divisor of two integers."""
    return str(math.gcd(a, b))


@tool
def lcm(a: int, b: int) -> str:
    """Return the least common multiple of two integers."""
    return str(math.lcm(a, b))


@tool
def is_prime(n: int) -> str:
    """Return whether an integer is prime."""
    if n < 2:
        return "False"
    for i in range(2, int(math.isqrt(n)) + 1):
        if n % i == 0:
            return "False"
    return "True"


@tool
def mean(numbers: list[float]) -> str:
    """Return the arithmetic mean of a list of numbers."""
    if not numbers:
        return "Error: empty list"
    return str(statistics.mean(numbers))


@tool
def median(numbers: list[float]) -> str:
    """Return the median of a list of numbers."""
    if not numbers:
        return "Error: empty list"
    return str(statistics.median(numbers))
