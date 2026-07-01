public class Main {
    public static void main(String[] args) {
        Solution s = new Solution();
        List<Boolean> correct = Arrays.asList(
                s.countNums(List.of()) == 0,
                s.countNums(Arrays.asList(-1, -2, 0)) == 0,
                s.countNums(Arrays.asList(1, 1, 2, -2, 3, 4, 5)) == 6,
                s.countNums(Arrays.asList(1, 6, 9, -6, 0, 1, 5)) == 5,
                s.countNums(Arrays.asList(1, 100, 98, -7, 1, -1)) == 4,
                s.countNums(Arrays.asList(12, 23, 34, -45, -56, 0)) == 5,
                s.countNums(Arrays.asList(-0, (int) Math.pow(1, 0))) == 1,
                s.countNums(List.of(1)) == 1
        );
        if (correct.contains(false)) {
            throw new AssertionError();
        }
    }
}
