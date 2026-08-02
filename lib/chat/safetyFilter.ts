const DANGEROUS_TERMS = [
  "öngyilkosság",
  "gyilkosság",
  "méreg",
  "tiszafa",
  "cianid",
  "arzén",
  "gyilkos galóca",
  "THC",
  "kokain",
];

/** Prod safety filter — marad a TS proxyban (Fázis 2 döntés). */
export function applySafetyFilter(answer: string): string {
  if (DANGEROUS_TERMS.some((t) => answer.toLowerCase().includes(t))) {
    console.error("SAFETY TRIGGERED: Dangerous content detected!");
    return "Sajnálom, de technikai vagy biztonsági okokból erre a kérdésre nem válaszolhatok.";
  }
  return answer;
}
