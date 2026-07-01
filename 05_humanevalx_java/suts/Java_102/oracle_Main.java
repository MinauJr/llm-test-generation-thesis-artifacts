public class Main {
    public static void main(String[] args) {
        Solution s = new Solution();
        List<Boolean> correct = Arrays.asList(
                s.chooseNum(12, 15) == 14,
                s.chooseNum(13, 12) == -1,
                s.chooseNum(33, 12354) == 12354,
                s.chooseNum(5234, 5233) == -1,
                s.chooseNum(6, 29) == 28,
                s.chooseNum(27, 10) == -1,
                s.chooseNum(7, 7) == -1,
                s.chooseNum(546, 546) == 546
        );
        if (correct.contains(false)) {
            throw new AssertionError();
        }
    }
}
