public class Main {
    public static void main(String[] args) {
        Solution s = new Solution();
        List<Boolean> correct = Arrays.asList(
                s.triangleArea(3, 4, 5) == 6.00,
                s.triangleArea(1, 2, 10) == -1,
                s.triangleArea(4, 8, 5) == 8.18,
                s.triangleArea(2, 2, 2) == 1.73,
                s.triangleArea(1, 2, 3) == -1,
                s.triangleArea(10, 5, 7) == 16.25,
                s.triangleArea(2, 6, 3) == -1,
                s.triangleArea(1, 1, 1) == 0.43,
                s.triangleArea(2, 2, 10) == -1
        );
        if (correct.contains(false)) {
            throw new AssertionError();
        }
    }
}
