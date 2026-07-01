public class Main {
    public static void main(String[] args) {
        Solution s = new Solution();
        List<Boolean> correct = Arrays.asList(
                s.multiply(148, 412) == 16,
                s.multiply(19, 28) == 72,
                s.multiply(2020, 1851) == 0,
                s.multiply(14,-15) == 20,
                s.multiply(76, 67) == 42,
                s.multiply(17, 27) == 49,
                s.multiply(0, 1) == 0,
                s.multiply(0, 0) == 0
        );
        if (correct.contains(false)) {
            throw new AssertionError();
        }
    }
}
