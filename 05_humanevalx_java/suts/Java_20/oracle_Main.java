public class Main {
    public static void main(String[] args) {
        Solution s = new Solution();
        List<Boolean> correct = Arrays.asList(
                s.findClosestElements(new ArrayList<>(Arrays.asList(1.0, 2.0, 3.9, 4.0, 5.0, 2.2))).equals(Arrays.asList(3.9, 4.0)),
                s.findClosestElements(new ArrayList<>(Arrays.asList(1.0, 2.0, 5.9, 4.0, 5.0))).equals(Arrays.asList(5.0, 5.9)),
                s.findClosestElements(new ArrayList<>(Arrays.asList(1.0, 2.0, 3.0, 4.0, 5.0, 2.2))).equals(Arrays.asList(2.0, 2.2)),
                s.findClosestElements(new ArrayList<>(Arrays.asList(1.0, 2.0, 3.0, 4.0, 5.0, 2.0))).equals(Arrays.asList(2.0, 2.0)),
                s.findClosestElements(new ArrayList<>(Arrays.asList(1.1, 2.2, 3.1, 4.1, 5.1))).equals(Arrays.asList(2.2, 3.1))
        );
        if (correct.contains(false)) {
            throw new AssertionError();
        }
    }
}
