public class Main {
    public static void main(String[] args) {
        Solution s = new Solution();
        List<Boolean> correct = Arrays.asList(
                s.byLength(new ArrayList<>(Arrays.asList(2, 1, 1, 4, 5, 8, 2, 3))).equals(Arrays.asList("Eight", "Five", "Four", "Three", "Two", "Two", "One", "One" )),
                s.byLength(new ArrayList<>(List.of())).equals(List.of()),
                s.byLength(new ArrayList<>(Arrays.asList(1, -1, 55))).equals(List.of("One" )),
                s.byLength(new ArrayList<>(Arrays.asList(1, -1, 3, 2))).equals(Arrays.asList("Three", "Two", "One" )),
                s.byLength(new ArrayList<>(Arrays.asList(9, 4, 8))).equals(Arrays.asList("Nine", "Eight", "Four" ))
        );
        if (correct.contains(false)) {
            throw new AssertionError();
        }
    }
}
