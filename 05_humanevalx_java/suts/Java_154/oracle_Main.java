public class Main {
    public static void main(String[] args) {
        Solution s = new Solution();
        List<Boolean> correct = Arrays.asList(
                s.cycpatternCheck("xyzw", "xyw") == false,
                s.cycpatternCheck("yello", "ell") == true,
                s.cycpatternCheck("whattup", "ptut") == false,
                s.cycpatternCheck("efef", "fee") == true,
                s.cycpatternCheck("abab", "aabb") == false,
                s.cycpatternCheck("winemtt", "tinem") == true
        );
        if (correct.contains(false)) {
            throw new AssertionError();
        }
    }
}
