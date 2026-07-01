public class Main {
    public static void main(String[] args) {
        Solution s = new Solution();
        List<Boolean> correct = Arrays.asList(
                Objects.equals(s.intersection(Arrays.asList(1, 2), Arrays.asList(2, 3)), "NO" ),
                Objects.equals(s.intersection(Arrays.asList(-1, 1), Arrays.asList(0, 4)), "NO" ),
                Objects.equals(s.intersection(Arrays.asList(-3, -1), Arrays.asList(-5, 5)), "YES" ),
                Objects.equals(s.intersection(Arrays.asList(-2, 2), Arrays.asList(-4, 0)), "YES" ),
                Objects.equals(s.intersection(Arrays.asList(-11, 2), Arrays.asList(-1, -1)), "NO" ),
                Objects.equals(s.intersection(Arrays.asList(1, 2), Arrays.asList(3, 5)), "NO" ),
                Objects.equals(s.intersection(Arrays.asList(1, 2), Arrays.asList(1, 2)), "NO" ),
                Objects.equals(s.intersection(Arrays.asList(-2, -2), Arrays.asList(-3, -2)), "NO" )
        );
        if (correct.contains(false)) {
            throw new AssertionError();
        }
    }
}
