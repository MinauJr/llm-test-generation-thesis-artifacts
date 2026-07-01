import java.util.*;
import java.lang.*;

class Solution {
    /**
    Input to this function is a string represented multiple groups for nested parentheses separated by spaces.
    For each of the group, output the deepest level of nesting of parentheses.
    E.g. (()()) has maximum two levels of nesting while ((())) has three.

    >>> parseNestedParens("(()()) ((())) () ((())()())")
    [2, 3, 1, 3]
     */
    public List<Integer> parseNestedParens(String paren_string) {
