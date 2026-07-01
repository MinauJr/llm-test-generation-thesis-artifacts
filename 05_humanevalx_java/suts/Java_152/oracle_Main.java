public class Main {
    public static void main(String[] args) {
        Solution s = new Solution();
        List<Boolean> correct = Arrays.asList(
                s.compare(Arrays.asList(1, 2, 3, 4, 5, 1), Arrays.asList(1, 2, 3, 4, 2, -2)).equals(Arrays.asList(0, 0, 0, 0, 3, 3)),
                s.compare(Arrays.asList(0,5,0,0,0,4), Arrays.asList(4,1,1,0,0,-2)).equals(Arrays.asList(4,4,1,0,0,6)),
                s.compare(Arrays.asList(1, 2, 3, 4, 5, 1), Arrays.asList(1, 2, 3, 4, 2, -2)).equals(Arrays.asList(0, 0, 0, 0, 3, 3)),
                s.compare(Arrays.asList(0, 0, 0, 0, 0, 0), Arrays.asList(0, 0, 0, 0, 0, 0)).equals(Arrays.asList(0, 0, 0, 0, 0, 0)),
                s.compare(Arrays.asList(1, 2, 3), Arrays.asList(-1, -2, -3)).equals(Arrays.asList(2, 4, 6)),
                s.compare(Arrays.asList(1, 2, 3, 5), Arrays.asList(-1, 2, 3, 4)).equals(Arrays.asList(2, 0, 0, 1))
        );
        if (correct.contains(false)) {
            throw new AssertionError();
        }
    }
}
