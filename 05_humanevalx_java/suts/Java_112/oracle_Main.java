public class Main {
    public static void main(String[] args) {
        Solution s = new Solution();
        List<Boolean> correct = Arrays.asList(
                s.reverseDelete("abcde", "ae" ).equals(Arrays.asList("bcd", false)),
                s.reverseDelete("abcdef", "b" ).equals(Arrays.asList("acdef", false)),
                s.reverseDelete("abcdedcba", "ab" ).equals(Arrays.asList("cdedc", true)),
                s.reverseDelete("dwik", "w" ).equals(Arrays.asList("dik", false)),
                s.reverseDelete("a", "a" ).equals(Arrays.asList("", true)),
                s.reverseDelete("abcdedcba", "" ).equals(Arrays.asList("abcdedcba", true)),
                s.reverseDelete("abcdedcba", "v" ).equals(Arrays.asList("abcdedcba", true)),
                s.reverseDelete("vabba", "v" ).equals(Arrays.asList("abba", true)),
                s.reverseDelete("mamma", "mia" ).equals(Arrays.asList("", true))
        );
        if (correct.contains(false)) {
            throw new AssertionError();
        }
    }
}
