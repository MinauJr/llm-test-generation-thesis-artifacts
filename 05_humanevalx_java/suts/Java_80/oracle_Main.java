public class Main {
    public static void main(String[] args) {
        Solution s = new Solution();
        List<Boolean> correct = Arrays.asList(
                !s.isHappy("a"),
                !s.isHappy("aa"),
                s.isHappy("abcd"),
                !s.isHappy("aabb"),
                s.isHappy("adb"),
                !s.isHappy("xyy"),
                s.isHappy("iopaxpoi"),
                !s.isHappy("iopaxioi")
        );
        if (correct.contains(false)) {
            throw new AssertionError();
        }
    }
}
