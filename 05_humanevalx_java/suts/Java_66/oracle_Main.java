public class Main {
    public static void main(String[] args) {
        Solution s = new Solution();
        List<Boolean> correct = Arrays.asList(
                s.digitSum("") == 0,
                s.digitSum("abAB") == 131,
                s.digitSum("abcCd") == 67,
                s.digitSum("helloE") == 69,
                s.digitSum("woArBld") == 131,
                s.digitSum("aAaaaXa") == 153,
                s.digitSum(" How are yOu?") == 151,
                s.digitSum("You arE Very Smart") == 327
        );
        if (correct.contains(false)) {
            throw new AssertionError();
        }
    }
}
