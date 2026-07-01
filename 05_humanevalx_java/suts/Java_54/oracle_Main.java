public class Main {
    public static void main(String[] args) {
        Solution s = new Solution();
        List<Boolean> correct = Arrays.asList(
                s.sameChars("eabcdzzzz", "dddzzzzzzzddeddabc"),
                s.sameChars("abcd", "dddddddabc"),
                s.sameChars("dddddddabc", "abcd"),
                !s.sameChars("eabcd", "dddddddabc"),
                !s.sameChars("abcd", "dddddddabcf"),
                !s.sameChars("eabcdzzzz", "dddzzzzzzzddddabc"),
                !s.sameChars("aabb", "aaccc")
        );
        if (correct.contains(false)) {
            throw new AssertionError();
        }
    }
}
