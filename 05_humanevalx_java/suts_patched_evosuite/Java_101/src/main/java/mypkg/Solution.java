package mypkg;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;

public class Solution {
    /**
     * You will be given a string of words separated by commas or spaces.
     * Your task is to split the string into words and return a list of the words.
     */
    public static List<String> wordsString(String s) {
        if (s == null || s.length() == 0) {
            return new ArrayList<>();
        }

        String normalised = s.replace(',', ' ').trim();
        if (normalised.isEmpty()) {
            return new ArrayList<>();
        }

        return new ArrayList<>(Arrays.asList(normalised.split("\\s+")));
    }

    public static List<String> wordStrings(String s) {
        return wordsString(s);
    }
}
