public class Main {
    public static void main(String[] args) {
        Solution s = new Solution();
        List<Boolean> correct = Arrays.asList(
                s.hexKey("AB") == 1,
                s.hexKey("1077E") == 2,
                s.hexKey("ABED1A33") == 4,
                s.hexKey("2020") == 2,
                s.hexKey("123456789ABCDEF0") == 6,
                s.hexKey("112233445566778899AABBCCDDEEFF00") == 12,
                s.hexKey("") == 0
        );
        if (correct.contains(false)) {
            throw new AssertionError();
        }
    }
}
