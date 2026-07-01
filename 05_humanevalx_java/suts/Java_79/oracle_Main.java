public class Main {
    public static void main(String[] args) {
        Solution s = new Solution();
        List<Boolean> correct = Arrays.asList(
                Objects.equals(s.decimalToBinary(0), "db0db"),
                Objects.equals(s.decimalToBinary(32), "db100000db"),
                Objects.equals(s.decimalToBinary(103), "db1100111db"),
                Objects.equals(s.decimalToBinary(15), "db1111db")
        );
        if (correct.contains(false)) {
            throw new AssertionError();
        }
    }
}
