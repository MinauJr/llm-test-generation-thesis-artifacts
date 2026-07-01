public class Main {
    public static void main(String[] args) {
        Solution s = new Solution();
        List<Boolean> correct = Arrays.asList(
                s.iscube(1),
                !s.iscube(2),
                s.iscube(-1),
                s.iscube(64),
                !s.iscube(180),
                s.iscube(1000),
                s.iscube(0),
                !s.iscube(1729)
        );
        if (correct.contains(false)) {
            throw new AssertionError();
        }
    }
}
