public class Main {
    public static void main(String[] args) {
        Solution s = new Solution();
        List<Boolean> correct = Arrays.asList(
                Objects.equals(s.filenameCheck("example.txt" ), "Yes" ),
                Objects.equals(s.filenameCheck("1example.dll" ), "No" ),
                Objects.equals(s.filenameCheck("s1sdf3.asd" ), "No" ),
                Objects.equals(s.filenameCheck("K.dll" ), "Yes" ),
                Objects.equals(s.filenameCheck("MY16FILE3.exe" ), "Yes" ),
                Objects.equals(s.filenameCheck("His12FILE94.exe" ), "No" ),
                Objects.equals(s.filenameCheck("_Y.txt" ), "No" ),
                Objects.equals(s.filenameCheck("?aREYA.exe" ), "No" ),
                Objects.equals(s.filenameCheck("/this_is_valid.dll" ), "No" ),
                Objects.equals(s.filenameCheck("this_is_valid.wow" ), "No" ),
                Objects.equals(s.filenameCheck("this_is_valid.txt" ), "Yes" ),
                Objects.equals(s.filenameCheck("this_is_valid.txtexe" ), "No" ),
                Objects.equals(s.filenameCheck("#this2_i4s_5valid.ten" ), "No" ),
                Objects.equals(s.filenameCheck("@this1_is6_valid.exe" ), "No" ),
                Objects.equals(s.filenameCheck("this_is_12valid.6exe4.txt" ), "No" ),
                Objects.equals(s.filenameCheck("all.exe.txt" ), "No" ),
                Objects.equals(s.filenameCheck("I563_No.exe" ), "Yes" ),
                Objects.equals(s.filenameCheck("Is3youfault.txt" ), "Yes" ),
                Objects.equals(s.filenameCheck("no_one#knows.dll" ), "Yes" ),
                Objects.equals(s.filenameCheck("1I563_Yes3.exe" ), "No" ),
                Objects.equals(s.filenameCheck("I563_Yes3.txtt" ), "No" ),
                Objects.equals(s.filenameCheck("final..txt" ), "No" ),
                Objects.equals(s.filenameCheck("final132" ), "No" ),
                Objects.equals(s.filenameCheck("_f4indsartal132." ), "No" )
        );
        if (correct.contains(false)) {
            throw new AssertionError();
        }
    }
}
