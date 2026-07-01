public class Main {
    public static void main(String[] args) {
        Solution s = new Solution();
        List<Boolean> correct = Arrays.asList(
                s.oddCount(List.of("1234567" )).equals(List.of("the number of odd elements 4n the str4ng 4 of the 4nput." )),
                s.oddCount(Arrays.asList("3", "11111111" )).equals(Arrays.asList("the number of odd elements 1n the str1ng 1 of the 1nput.", "the number of odd elements 8n the str8ng 8 of the 8nput." )),
                s.oddCount(Arrays.asList("271", "137", "314" )).equals(Arrays.asList(
                        "the number of odd elements 2n the str2ng 2 of the 2nput.",
                        "the number of odd elements 3n the str3ng 3 of the 3nput.",
                        "the number of odd elements 2n the str2ng 2 of the 2nput."
                ))
        );
        if (correct.contains(false)) {
            throw new AssertionError();
        }
    }
}
