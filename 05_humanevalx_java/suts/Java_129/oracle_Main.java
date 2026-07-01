public class Main {
    public static void main(String[] args) {
        Solution s = new Solution();
        List<Boolean> correct = Arrays.asList(
                s.minPath(Arrays.asList(Arrays.asList(1, 2, 3), Arrays.asList(4, 5, 6), Arrays.asList(7, 8, 9)), 3).equals(Arrays.asList(1, 2, 1)),
                s.minPath(Arrays.asList(Arrays.asList(5, 9, 3), Arrays.asList(4, 1, 6), Arrays.asList(7, 8, 2)), 1).equals(List.of(1)),
                s.minPath(Arrays.asList(Arrays.asList(1, 2, 3, 4), Arrays.asList(5, 6, 7, 8), Arrays.asList(9, 10, 11, 12), Arrays.asList(13, 14, 15, 16)), 4).equals(Arrays.asList(1, 2, 1, 2)),
                s.minPath(Arrays.asList(Arrays.asList(6, 4, 13, 10), Arrays.asList(5, 7, 12, 1), Arrays.asList(3, 16, 11, 15), Arrays.asList(8, 14, 9, 2)), 7).equals(Arrays.asList(1, 10, 1, 10, 1, 10, 1)),
                s.minPath(Arrays.asList(Arrays.asList(8, 14, 9, 2), Arrays.asList(6, 4, 13, 15), Arrays.asList(5, 7, 1, 12), Arrays.asList(3, 10, 11, 16)), 5).equals(Arrays.asList(1, 7, 1, 7, 1)),
                s.minPath(Arrays.asList(Arrays.asList(11, 8, 7, 2), Arrays.asList(5, 16, 14, 4), Arrays.asList(9, 3, 15, 6), Arrays.asList(12, 13, 10, 1)), 9).equals(Arrays.asList(1, 6, 1, 6, 1, 6, 1, 6, 1)),
                s.minPath(Arrays.asList(Arrays.asList(12, 13, 10, 1), Arrays.asList(9, 3, 15, 6), Arrays.asList(5, 16, 14, 4), Arrays.asList(11, 8, 7, 2)), 12).equals(Arrays.asList(1, 6, 1, 6, 1, 6, 1, 6, 1, 6, 1, 6)),
                s.minPath(Arrays.asList(Arrays.asList(2, 7, 4), Arrays.asList(3, 1, 5), Arrays.asList(6, 8, 9)), 8).equals(Arrays.asList(1, 3, 1, 3, 1, 3, 1, 3)),
                s.minPath(Arrays.asList(Arrays.asList(6, 1, 5), Arrays.asList(3, 8, 9), Arrays.asList(2, 7, 4)), 8).equals(Arrays.asList(1, 5, 1, 5, 1, 5, 1, 5)),
                s.minPath(Arrays.asList(Arrays.asList(1, 2), Arrays.asList(3, 4)), 10).equals(Arrays.asList(1, 2, 1, 2, 1, 2, 1, 2, 1, 2)),
                s.minPath(Arrays.asList(Arrays.asList(1, 3), Arrays.asList(3, 2)), 10).equals(Arrays.asList(1, 3, 1, 3, 1, 3, 1, 3, 1, 3))
        );
        if (correct.contains(false)) {
            throw new AssertionError();
        }
    }
}
