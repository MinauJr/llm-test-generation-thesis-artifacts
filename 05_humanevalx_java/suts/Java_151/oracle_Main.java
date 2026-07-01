public class Main {
    public static void main(String[] args) {
        Solution s = new Solution();
        List<Boolean> correct = Arrays.asList(
                s.doubleTheDifference(List.of()) == 0,
                s.doubleTheDifference(Arrays.asList(5, 4)) == 25,
                s.doubleTheDifference(Arrays.asList(0.1, 0.2, 0.3)) == 0,
                s.doubleTheDifference(Arrays.asList(-10, -20, -30)) == 0,
                s.doubleTheDifference(Arrays.asList(-1, -2, 8)) == 0,
                s.doubleTheDifference(Arrays.asList(0.2, 3, 5)) == 34
        );
        if (correct.contains(false)) {
            throw new AssertionError();
        }
        List<Object> lst = new ArrayList<>();
        for (int i = -99; i < 100; i += 2) {
            lst.add(i);
        }
        int odd_sum = lst.stream().filter(i -> i instanceof Integer p && p % 2 != 0 && p > 0).map(i -> (Integer) i * (Integer) i).reduce(Integer::sum).orElse(0);
        assert s.doubleTheDifference(lst) == odd_sum;
    }
}
