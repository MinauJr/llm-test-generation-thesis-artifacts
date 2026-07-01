public class Main {
    public static void main(String[] args) {
        Solution s = new Solution();
        List<Boolean> correct = Arrays.asList(
                s.triangleArea(5, 3) == 7.5,
                s.triangleArea(2, 2) == 2.0,
                s.triangleArea(10, 8) == 40.0
        );
        if (correct.contains(false)) {
            throw new AssertionError();
        }
    }
}
