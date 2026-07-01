public class Main {
    public static void main(String[] args) {
        Solution s = new Solution();
        List<Boolean> correct = Arrays.asList(
                s.median(new ArrayList<>(Arrays.asList(3, 1, 2, 4, 5))) == 3,
                s.median(new ArrayList<>(Arrays.asList(-10, 4, 6, 1000, 10, 20))) == 8.0,
                s.median(new ArrayList<>(Arrays.asList(5))) == 5,
                s.median(new ArrayList<>(Arrays.asList(6, 5))) == 5.5
        );
        if (correct.contains(false)) {
            throw new AssertionError();
        }
    }
}
