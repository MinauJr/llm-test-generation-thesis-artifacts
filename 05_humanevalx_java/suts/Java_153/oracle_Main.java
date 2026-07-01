public class Main {
    public static void main(String[] args) {
        Solution s = new Solution();
        List<Boolean> correct = Arrays.asList(
                Objects.equals(s.StrongestExtension("Watashi", Arrays.asList("tEN", "niNE", "eIGHt8OKe")), "Watashi.eIGHt8OKe"),
                Objects.equals(s.StrongestExtension("Boku123", Arrays.asList("nani", "NazeDa", "YEs.WeCaNe", "32145tggg")), "Boku123.YEs.WeCaNe"),
                Objects.equals(s.StrongestExtension("__YESIMHERE", Arrays.asList("t", "eMptY", "nothing", "zeR00", "NuLl__", "123NoooneB321")), "__YESIMHERE.NuLl__"),
                Objects.equals(s.StrongestExtension("K", Arrays.asList("Ta", "TAR", "t234An", "cosSo")), "K.TAR"),
                Objects.equals(s.StrongestExtension("__HAHA", Arrays.asList("Tab", "123", "781345", "-_-")), "__HAHA.123"),
                Objects.equals(s.StrongestExtension("YameRore", Arrays.asList("HhAas", "okIWILL123", "WorkOut", "Fails", "-_-")), "YameRore.okIWILL123"),
                Objects.equals(s.StrongestExtension("finNNalLLly", Arrays.asList("Die", "NowW", "Wow", "WoW")), "finNNalLLly.WoW"),
                Objects.equals(s.StrongestExtension("_", Arrays.asList("Bb", "91245")), "_.Bb"),
                Objects.equals(s.StrongestExtension("Sp", Arrays.asList("671235", "Bb")), "Sp.671235")
        );
        if (correct.contains(false)) {
            throw new AssertionError();
        }
    }
}
