public class Main {
    public static void main(String[] args) {
        Solution s = new Solution();
        List<Boolean> correct = Arrays.asList(
                s.isPalindrome(""),
                s.isPalindrome("aba"),
                s.isPalindrome("aaaaa"),
                !s.isPalindrome("zbcd"),
                s.isPalindrome("xywyx"),
                !s.isPalindrome("xywyz"),
                !s.isPalindrome("xywzx")
        );
        if (correct.contains(false)) {
            throw new AssertionError();
        }
    }
}
