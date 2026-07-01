public class Main {
    public static void main(String[] args) {
        Solution s = new Solution();
        List<Boolean> correct = Arrays.asList(
                s.orderByPoints(new ArrayList<>(Arrays.asList(1, 11, -1, -11, -12))).equals(Arrays.asList(-1, -11, 1, -12, 11)),
                s.orderByPoints(new ArrayList<>(Arrays.asList(1234, 423, 463, 145, 2, 423, 423, 53, 6, 37, 3457, 3, 56, 0, 46))).equals(Arrays.asList(0, 2, 3, 6, 53, 423, 423, 423, 1234, 145, 37, 46, 56, 463, 3457)),
                s.orderByPoints(new ArrayList<>(List.of())).equals(List.of()),
                s.orderByPoints(new ArrayList<>(Arrays.asList(1, -11, -32, 43, 54, -98, 2, -3))).equals(Arrays.asList(-3, -32, -98, -11, 1, 2, 43, 54)),
                s.orderByPoints(new ArrayList<>(Arrays.asList(1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11))).equals(Arrays.asList(1, 10, 2, 11, 3, 4, 5, 6, 7, 8, 9)),
                s.orderByPoints(new ArrayList<>(Arrays.asList(0, 6, 6, -76, -21, 23, 4))).equals(Arrays.asList(-76, -21, 0, 4, 23, 6, 6))
        );
        if (correct.contains(false)) {
            throw new AssertionError();
        }
    }
}
