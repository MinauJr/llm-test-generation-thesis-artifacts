public class Main {
    public static void main(String[] args) {
        Solution s = new Solution();
        List<Boolean> correct = Arrays.asList(
                s.sumSquares(Arrays.asList(1., 2., 3.)) == 14,
                s.sumSquares(Arrays.asList(1.0, 2., 3.)) == 14,
                s.sumSquares(Arrays.asList(1., 3., 5., 7.)) == 84,
                s.sumSquares(Arrays.asList(1.4, 4.2, 0.)) == 29,
                s.sumSquares(Arrays.asList(-2.4, 1., 1.)) == 6,
                s.sumSquares(Arrays.asList(100., 1., 15., 2.)) == 10230,
                s.sumSquares(Arrays.asList(10000., 10000.)) == 200000000,
                s.sumSquares(Arrays.asList(-1.4, 4.6, 6.3)) == 75,
                s.sumSquares(Arrays.asList(-1.4, 17.9, 18.9, 19.9)) == 1086,
                s.sumSquares(List.of(0.)) == 0,
                s.sumSquares(List.of(-1.)) == 1,
                s.sumSquares(Arrays.asList(-1., 1., 0.)) == 2
        );
        if (correct.contains(false)) {
            throw new AssertionError();
        }
    }
}
