public class Main {
    public static void main(String[] args) {
        Solution s = new Solution();
        List<Boolean> correct = Arrays.asList(
                s.modp(3, 5) == 3,
                s.modp(1101, 101) == 2,
                s.modp(0, 101) == 1,
                s.modp(3, 11) == 8,
                s.modp(100, 101) == 1,
                s.modp(30, 5) == 4,
                s.modp(31, 5) == 3
        );
        if (correct.contains(false)) {
            throw new AssertionError();
        }
    }
}
