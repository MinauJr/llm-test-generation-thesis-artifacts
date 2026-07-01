public class Main {
    public static void main(String[] args) {
        Solution s = new Solution();
        List<Boolean> correct = Arrays.asList(
                s.moveOneBall(new ArrayList<>(Arrays.asList(3, 4, 5, 1, 2))) == true,
                s.moveOneBall(new ArrayList<>(Arrays.asList(3, 5, 10, 1, 2))) == true,
                s.moveOneBall(new ArrayList<>(Arrays.asList(4, 3, 1, 2))) == false,
                s.moveOneBall(new ArrayList<>(Arrays.asList(3, 5, 4, 1, 2))) == false,
                s.moveOneBall(new ArrayList<>(Arrays.asList())) == true
        );
        if (correct.contains(false)) {
            throw new AssertionError();
        }
    }
}
