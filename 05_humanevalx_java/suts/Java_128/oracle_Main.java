public class Main {
    public static void main(String[] args) {
        Solution s = new Solution();
        List<Boolean> correct = Arrays.asList(
                s.prodSigns(Arrays.asList(1, 2, 2, -4)).get() == -9,
                s.prodSigns(Arrays.asList(0, 1)).get() == 0,
                s.prodSigns(Arrays.asList(1, 1, 1, 2, 3, -1, 1)).get() == -10,
                s.prodSigns(List.of()).isEmpty(),
                s.prodSigns(Arrays.asList(2, 4,1, 2, -1, -1, 9)).get() == 20,
                s.prodSigns(Arrays.asList(-1, 1, -1, 1)).get() == 4,
                s.prodSigns(Arrays.asList(-1, 1, 1, 1)).get() == -4,
                s.prodSigns(Arrays.asList(-1, 1, 1, 0)).get() == 0
        );
        if (correct.contains(false)) {
            throw new AssertionError();
        }
    }
}
