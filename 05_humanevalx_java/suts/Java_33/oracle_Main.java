public class Main {
    public static void main(String[] args) {
        Solution s = new Solution();
        List<Boolean> correct = Arrays.asList(
                s.sortThird(new ArrayList<>(Arrays.asList(5, 6, 3, 4, 8, 9, 2))).equals(Arrays.asList(2, 6, 3, 4, 8, 9, 5)),
                s.sortThird(new ArrayList<>(Arrays.asList(5, 8, 3, 4, 6, 9, 2))).equals(Arrays.asList(2, 8, 3, 4, 6, 9, 5)),
                s.sortThird(new ArrayList<>(Arrays.asList(5, 6, 9, 4, 8, 3, 2))).equals(Arrays.asList(2, 6, 9, 4, 8, 3, 5)),
                s.sortThird(new ArrayList<>(Arrays.asList(5, 6, 3, 4, 8, 9, 2, 1))).equals(Arrays.asList(2, 6, 3, 4, 8, 9, 5, 1))
        );
        if (correct.contains(false)) {
            throw new AssertionError();
        }
    }
}
