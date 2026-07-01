public class Main {
    public static void main(String[] args) {
        Solution s = new Solution();
        List<Boolean> correct = Arrays.asList(
                s.addElements(Arrays.asList(1, -2, -3, 41, 57, 76, 87, 88, 99), 3) == -4,
                s.addElements(Arrays.asList(111, 121, 3, 4000, 5, 6), 2) == 0,
                s.addElements(Arrays.asList(11, 21, 3, 90, 5, 6, 7, 8, 9), 4) == 125,
                s.addElements(Arrays.asList(111, 21, 3, 4000, 5, 6, 7, 8, 9), 4) == 24,
                s.addElements(Arrays.asList(1), 1) == 1
        );
        if (correct.contains(false)) {
            throw new AssertionError();
        }
    }
}
