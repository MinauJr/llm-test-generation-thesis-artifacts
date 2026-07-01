import java.util.*;
import java.lang.*;

class Solution {
    /**
    Given a map, return True if all keys are strings in lower
    case or all keys are strings in upper case, else return False.
    The function should return False is the given map is empty.
    Examples:
    checkDictCase({"a":"apple", "b":"banana"}) should return True.
    checkDictCase({"a":"apple", "A":"banana", "B":"banana"}) should return False.
    checkDictCase({"a":"apple", 8:"banana", "a":"apple"}) should return False.
    checkDictCase({"Name":"John", "Age":"36", "City":"Houston"}) should return False.
    checkDictCase({"STATE":"NC", "ZIP":"12345" }) should return True.
     */
    public boolean checkDictCase(Map<Object, Object> dict) {
