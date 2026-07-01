public class Main {
    public static void main(String[] args) {
        Solution s = new Solution();
        List<Boolean> correct = Arrays.asList(
                s.sortArray(new ArrayList<>(Arrays.asList(1, 5, 2, 3, 4))).equals(Arrays.asList(1, 2, 4, 3, 5)),
                s.sortArray(new ArrayList<>(Arrays.asList(-2, -3, -4, -5, -6))).equals(Arrays.asList(-4, -2, -6, -5, -3)),
                s.sortArray(new ArrayList<>(Arrays.asList(1, 0, 2, 3, 4))).equals(Arrays.asList(0, 1, 2, 4, 3)),
                s.sortArray(new ArrayList<>(List.of())).equals(List.of()),
                s.sortArray(new ArrayList<>(Arrays.asList(2, 5, 77, 4, 5, 3, 5, 7, 2, 3, 4))).equals(Arrays.asList(2, 2, 4, 4, 3, 3, 5, 5, 5, 7, 77)),
                s.sortArray(new ArrayList<>(Arrays.asList(3, 6, 44, 12, 32, 5))).equals(Arrays.asList(32, 3, 5, 6, 12, 44)),
                s.sortArray(new ArrayList<>(Arrays.asList(2, 4, 8, 16, 32))).equals(Arrays.asList(2, 4, 8, 16, 32)),
                s.sortArray(new ArrayList<>(Arrays.asList(2, 4, 8, 16, 32))).equals(Arrays.asList(2, 4, 8, 16, 32))
        );
        if (correct.contains(false)) {
            throw new AssertionError();
        }
    }
}
