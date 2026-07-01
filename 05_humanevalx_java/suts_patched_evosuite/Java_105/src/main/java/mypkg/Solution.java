package mypkg;

import java.util.*;
import java.lang.*;

public class Solution {
    /**
    Given an array of integers, sort the integers that are between 1 and 9 inclusive,
    reverse the resulting array, and then replace each digit by its corresponding name from
    "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine".

    For example:
      arr = [2, 1, 1, 4, 5, 8, 2, 3]
            -> sort arr -> [1, 1, 2, 2, 3, 4, 5, 8]
            -> reverse arr -> [8, 5, 4, 3, 2, 2, 1, 1]
      return ["Eight", "Five", "Four", "Three", "Two", "Two", "One", "One"]

      If the array is empty, return an empty array:
      arr = []
      return []

      If the array has any strange number ignore it:
      arr = [1, -1 , 55]
            -> sort arr -> [-1, 1, 55]
            -> reverse arr -> [55, 1, -1]
      return = ["One"]
     */
    public List<String> byLength(List<Integer> arr) {
List<Integer> sorted_arr = new ArrayList<>(arr);
        sorted_arr.sort(Collections.reverseOrder());
        List<String> new_arr = new ArrayList<>();
        for (int var : sorted_arr) {
            if (var >= 1 && var <= 9) {
                switch (var) {
                    case 1: new_arr.add("One"); break;
                    case 2: new_arr.add("Two"); break;
                    case 3: new_arr.add("Three"); break;
                    case 4: new_arr.add("Four"); break;
                    case 5: new_arr.add("Five"); break;
                    case 6: new_arr.add("Six"); break;
                    case 7: new_arr.add("Seven"); break;
                    case 8: new_arr.add("Eight"); break;
                    case 9: new_arr.add("Nine"); break;
                }
            }
        }
        return new_arr;
    }
}
