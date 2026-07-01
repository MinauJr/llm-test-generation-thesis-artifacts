package mypkg;

public class Solution {
    /**
     * You'll be given a string of words, and your task is to count the number
     * of boredoms. A boredom is a sentence that starts with the word "I".
     * Sentences are delimited by '.', '?' or '!'.
     */
    public static int isBored(String s) {
        String[] sentences = s.split("[.?!]\\s*");
        int count = 0;

        for (String sentence : sentences) {
            if (sentence.startsWith("I ")) {
                count++;
            }
        }
        return count;
    }
}
