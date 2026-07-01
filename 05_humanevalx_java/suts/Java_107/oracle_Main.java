public class Main {
    public static void main(String[] args) {
        Solution s = new Solution();
        List<Boolean> correct = Arrays.asList(
                s.evenOddPalindrome(123).equals(Arrays.asList(8, 13)),
                s.evenOddPalindrome(12).equals(Arrays.asList(4, 6)),
                s.evenOddPalindrome(3).equals(Arrays.asList(1, 2)),
                s.evenOddPalindrome(63).equals(Arrays.asList(6, 8)),
                s.evenOddPalindrome(25).equals(Arrays.asList(5, 6)),
                s.evenOddPalindrome(19).equals(Arrays.asList(4, 6)),
                s.evenOddPalindrome(9).equals(Arrays.asList(4, 5)),
                s.evenOddPalindrome(1).equals(Arrays.asList(0, 1))
        );
        if (correct.contains(false)) {
            throw new AssertionError();
        }
    }
}
