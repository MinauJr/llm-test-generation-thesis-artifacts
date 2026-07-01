public class Main {
    public static void main(String[] args) {
        Solution s = new Solution();
        List<Boolean> correct = Arrays.asList(
                s.canArrange(Arrays.asList(1, 2, 4, 3, 5)) == 3,
                s.canArrange(Arrays.asList(1, 2, 4, 5)) == -1,
                s.canArrange(Arrays.asList(1, 4, 2, 5, 6, 7, 8, 9, 10)) == 2,
                s.canArrange(Arrays.asList(4, 8, 5, 7, 3)) == 4,
                s.canArrange(List.of()) == -1
        );
        if (correct.contains(false)) {
            throw new AssertionError();
        }
    }
}
