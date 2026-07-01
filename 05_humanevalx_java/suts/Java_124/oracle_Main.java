public class Main {
    public static void main(String[] args) {
        Solution s = new Solution();
        List<Boolean> correct = Arrays.asList(
                s.validDate("03-11-2000" ) == true,
                s.validDate("15-01-2012" ) == false,
                s.validDate("04-0-2040" ) == false,
                s.validDate("06-04-2020" ) == true,
                s.validDate("01-01-2007" ) == true,
                s.validDate("03-32-2011" ) == false,
                s.validDate("" ) == false,
                s.validDate("04-31-3000" ) == false,
                s.validDate("06-06-2005" ) == true,
                s.validDate("21-31-2000" ) == false,
                s.validDate("04-12-2003" ) == true,
                s.validDate("04122003" ) == false,
                s.validDate("20030412" ) == false,
                s.validDate("2003-04" ) == false,
                s.validDate("2003-04-12" ) == false,
                s.validDate("04-2003" ) == false
        );
        if (correct.contains(false)) {
            throw new AssertionError();
        }
    }
}
