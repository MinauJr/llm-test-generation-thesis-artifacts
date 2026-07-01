public class Main {
    public static void main(String[] args) {
        Solution s = new Solution();
        List<Boolean> correct = Arrays.asList(
                Objects.equals(s.encrypt("hi"), "lm"),
                Objects.equals(s.encrypt("asdfghjkl"), "ewhjklnop"),
                Objects.equals(s.encrypt("gf"), "kj"),
                Objects.equals(s.encrypt("et"), "ix"),
                Objects.equals(s.encrypt("faewfawefaewg"), "jeiajeaijeiak"),
                Objects.equals(s.encrypt("hellomyfriend"), "lippsqcjvmirh"),
                Objects.equals(s.encrypt("dxzdlmnilfuhmilufhlihufnmlimnufhlimnufhfucufh"), "hbdhpqrmpjylqmpyjlpmlyjrqpmqryjlpmqryjljygyjl"),
                Objects.equals(s.encrypt("a"), "e")
        );
        if (correct.contains(false)) {
            throw new AssertionError();
        }
    }
}
