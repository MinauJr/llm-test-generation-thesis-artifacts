public class Main {
    public static void main(String[] args) {
        Solution s = new Solution();
        List<Boolean> correct = Arrays.asList(
                s.tri(3).equals(Arrays.asList(1, 3, 2, 8)),
                s.tri(4).equals(Arrays.asList(1, 3, 2, 8, 3)),
                s.tri(5).equals(Arrays.asList(1, 3, 2, 8, 3, 15)),
                s.tri(6).equals(Arrays.asList(1, 3, 2, 8, 3, 15, 4)),
                s.tri(7).equals(Arrays.asList(1, 3, 2, 8, 3, 15, 4, 24)),
                s.tri(8).equals(Arrays.asList(1, 3, 2, 8, 3, 15, 4, 24, 5)),
                s.tri(9).equals(Arrays.asList(1, 3, 2, 8, 3, 15, 4, 24, 5, 35)),
                s.tri(20).equals(Arrays.asList(1, 3, 2, 8, 3, 15, 4, 24, 5, 35, 6, 48, 7, 63, 8, 80, 9, 99, 10, 120, 11)),
                s.tri(0).equals(List.of(1)),
                s.tri(1).equals(Arrays.asList(1, 3))
        );
        if (correct.contains(false)) {
            throw new AssertionError();
        }
    }
}
