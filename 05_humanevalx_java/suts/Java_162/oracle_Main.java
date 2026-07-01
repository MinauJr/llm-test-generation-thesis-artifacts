public class Main {
    public static void main(String[] args) throws NoSuchAlgorithmException {
        Solution s = new Solution();
        List<Boolean> correct = Arrays.asList(
                s.stringToMd5("Hello world").get().equals("3e25960a79dbc69b674cd4ec67a72c62"),
                s.stringToMd5("").isEmpty(),
                s.stringToMd5("A B C").get().equals("0ef78513b0cb8cef12743f5aeb35f888"),
                s.stringToMd5("password").get().equals("5f4dcc3b5aa765d61d8327deb882cf99")
        );
        if (correct.contains(false)) {
            throw new AssertionError();
        }
    }
}
