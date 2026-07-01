public class Main {
    public static void main(String[] args) {
        Solution s = new Solution();
        List<Boolean> correct = Arrays.asList(
                s.getMaxTriples(5) == 1,
                s.getMaxTriples(6) == 4,
                s.getMaxTriples(10) == 36,
                s.getMaxTriples(100) == 53361
        );
        if (correct.contains(false)) {
            throw new AssertionError();
        }
    }
}
