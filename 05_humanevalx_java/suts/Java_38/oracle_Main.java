public class Main {
    static char[] letters = "abcdefghijklmnopqrstuvwxyz".toCharArray();
    static Random rand = new Random(42);
    public static String random_string(int length) {
        StringBuilder sb = new StringBuilder();
        for (int i = 0; i < length; i++) {
            sb.append(letters[rand.nextInt(26)]);
        }
        return sb.toString();
    }
    public static void main(String[] args) {
        Solution s = new Solution();
        for (int i = 0; i < 100; i++) {
            String str = random_string(rand.nextInt(10) + 10);
            String encode_str = s.encodeCyclic(str);
            if (!s.decodeCyclic(encode_str).equals(str)) {
                throw new AssertionError();
            }
        }
    }
}
