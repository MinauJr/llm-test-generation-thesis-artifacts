public class Main {
    public static void main(String[] args) {
        Solution s = new Solution();
        List<Boolean> correct = Arrays.asList(
                s.fibfib(2) == 1,
                s.fibfib(1) == 0,
                s.fibfib(5) == 4,
                s.fibfib(8) == 24,
                s.fibfib(10) == 81,
                s.fibfib(12) == 274,
                s.fibfib(14) == 927
        );
        if (correct.contains(false)) {
            throw new AssertionError();
        }
    }
}
