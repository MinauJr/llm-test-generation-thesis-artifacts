public class Main {
    public static void main(String[] args) {
        Solution s = new Solution();
        List<Boolean> correct = Arrays.asList(
                s.largestPrimeFactor(15) == 5,
                s.largestPrimeFactor(27) == 3,
                s.largestPrimeFactor(63) == 7,
                s.largestPrimeFactor(330) == 11,
                s.largestPrimeFactor(13195) == 29
        );
        if (correct.contains(false)) {
            throw new AssertionError();
        }
    }
}
