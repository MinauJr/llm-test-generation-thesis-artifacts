public class Main {
    public static void main(String[] args) {
        Solution s = new Solution();
        List<Boolean> correct = Arrays.asList(
                Objects.equals((String) s.roundedAvg(1, 5), "11" ),
                Objects.equals((String) s.roundedAvg(7, 13), "1010" ),
                Objects.equals((String) s.roundedAvg(964, 977), "1111001011" ),
                Objects.equals((String) s.roundedAvg(996, 997), "1111100101" ),
                Objects.equals((String) s.roundedAvg(560, 851), "1011000010" ),
                Objects.equals((String) s.roundedAvg(185, 546), "101101110" ),
                Objects.equals((String) s.roundedAvg(362, 496), "110101101" ),
                Objects.equals((String) s.roundedAvg(350, 902), "1001110010" ),
                Objects.equals((String) s.roundedAvg(197, 233), "11010111" ),
                (int) s.roundedAvg(7, 5) == -1,
                (int) s.roundedAvg(5, 1) == -1,
                Objects.equals((String) s.roundedAvg(5, 5), "101" )
        );
        if (correct.contains(false)) {
            throw new AssertionError();
        }
    }
}
