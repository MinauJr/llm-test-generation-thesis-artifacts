public class Main {
    public static void main(String[] args) {
        Solution s = new Solution();
        Random rand = new Random(42);
        for (int i = 0; i < 100; i++) {
            int ncoeff = 2 * (rand.nextInt(3) + 1);
            List<Double> coeffs = new ArrayList<>();
            for (int j = 0; j < ncoeff; j++) {
                int coeff = rand.nextInt(20) - 10;
                if (coeff == 0) {
                    coeff = 1;
                }
                coeffs.add((double) coeff);
            }
            double solution = s.findZero(coeffs);
            if (Math.abs(s.poly(coeffs, solution)) > 1e-4) {
                throw new AssertionError();
            }
        }
    }
}
