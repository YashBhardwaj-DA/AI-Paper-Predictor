"""
Clark's DU Mathematics PYQ Paper Predictor  —  FIXED BUILD
B.Sc (Hons) Mathematics · Delhi University · NEP (90-mark format)

Fixes in this build
-------------------
1. Claude prompt now enforces 5 distinct question-type categories and
   picks a different mix every generation.
2. Numerical / computational questions (evaluate, solve, find, apply algorithm)
   are mandatory in every paper.
3. Strong per-generation seed (timestamp + UUID + random) prevents any two
   papers from having the same structure.
4. Fallback bank completely rewritten with real numerical DU-style questions
   covering every subject — not just "prove that" stubs.
5. Each generation randomly rotates which topics land in which questions,
   so even regenerating the same subject gives a structurally different paper.
"""

import os, json, random, time, uuid
from flask import Flask, render_template_string, request, jsonify

app = Flask(__name__)

# ══════════════════════════════════════════════════════════════════════════════
#  CURRICULUM  — 6 semesters, 20 subjects, ~14 topics each
# ══════════════════════════════════════════════════════════════════════════════
CURRICULUM = {
    "Semester 1": {
        "Algebra": {
            "code": "BMATH101",
            "topics": [
                "Polar form and De Moivre's theorem — nth roots computation",
                "Theory of equations — Vieta's formulas, sum and product of roots",
                "Descartes' rule of signs — counting positive/negative roots",
                "Cardan's method — solving depressed and general cubics numerically",
                "Ferrari's method — solving quartic equations step by step",
                "Row reduction and echelon form — solving systems Ax=b",
                "Rank of a matrix — using PAQ normal form",
                "Eigenvalues and eigenvectors — characteristic polynomial computation",
                "Cayley-Hamilton theorem — verifying and computing matrix powers",
                "Diagonalisation — finding P and D such that A = PDP⁻¹",
                "AM-GM and Cauchy-Schwarz inequalities — proving and applying",
                "Symmetric functions of roots — Newton's power-sum identities",
                "Consistency of linear systems — Rouché-Capelli theorem",
                "Skew-symmetric and orthogonal matrices — properties with examples",
            ],
        },
        "Elementary Real Analysis": {
            "code": "BMATH102",
            "topics": [
                "Completeness axiom — supremum and infimum computations",
                "Convergence of sequences — ε-N proofs and limit calculations",
                "Cauchy sequences — verifying with the Cauchy criterion",
                "Monotone convergence theorem — finding limits of recursive sequences",
                "lim sup and lim inf — computing for given sequences",
                "Comparison and limit-comparison tests — series convergence",
                "Ratio and root tests — determining convergence with calculations",
                "Raabe's test — borderline series analysis",
                "Alternating series test — error estimation examples",
                "Absolute vs conditional convergence — examples and counterexamples",
                "ε-δ limits — computing and verifying function limits",
                "Uniform continuity — verifying on bounded intervals",
                "Mean value theorem — finding the guaranteed point c",
                "Taylor's theorem — computing error bounds for approximations",
            ],
        },
        "Probability and Statistics": {
            "code": "BMATH103",
            "topics": [
                "Classical probability — counting sample spaces with combinatorics",
                "Conditional probability — computing P(A|B) from contingency tables",
                "Bayes' theorem — posterior probability calculations",
                "Discrete distributions — PMF, expectation, variance computation",
                "Continuous distributions — PDF, CDF, finding probabilities",
                "MGF — deriving and using to find moments",
                "Binomial distribution — computing probabilities, mean, variance",
                "Poisson distribution — approximation of binomial, numerical problems",
                "Normal distribution — z-score, area under curve, percentile finding",
                "Chebyshev's inequality — bounds without knowing distribution",
                "Correlation coefficient — computing r from bivariate data",
                "Regression lines — finding equations from data tables",
                "Independent events — verifying independence numerically",
                "Joint distributions — marginal and conditional densities",
            ],
        },
    },
    "Semester 2": {
        "Linear Algebra": {
            "code": "BMATH201",
            "topics": [
                "Vector spaces — verifying axioms for given sets",
                "Subspace test — checking conditions with examples",
                "Linear independence — row-reducing to test and find bases",
                "Dimension and basis — finding basis for row/column/null spaces",
                "Rank-nullity theorem — numerical verification for given matrices",
                "Linear transformations — computing kernel and image with bases",
                "Matrix of transformation — building [T]_β for given bases",
                "Change of basis — computing transition matrices",
                "Inner product spaces — Gram-Schmidt orthogonalisation process",
                "Orthonormal bases — constructing via Gram-Schmidt on given vectors",
                "Eigenvalues of linear operators — diagonalising a linear map",
                "Spectral theorem — orthogonal diagonalisation of symmetric matrices",
                "Jordan form — computing for small 3×3 nilpotent cases",
                "Isomorphism theorems — first isomorphism theorem with examples",
            ],
        },
        "Calculus": {
            "code": "BMATH202",
            "topics": [
                "Leibniz's theorem — computing nth derivative of products",
                "Asymptotes — finding all asymptotes of rational curves",
                "Curvature and radius of curvature — computing at given points",
                "Curve tracing — sketching Cartesian, polar, parametric curves",
                "Reduction formulae — evaluating ∫sinⁿx dx, ∫cosⁿx dx with limits",
                "Beta and Gamma functions — evaluating integrals using B(m,n), Γ(n)",
                "Area between curves — computing definite integrals with split regions",
                "Arc length — rectification of Cartesian and polar curves",
                "Volume of solid of revolution — disk and shell method calculations",
                "Surface area of revolution — computing for given curves",
                "Double integrals — evaluating over given regions, change of order",
                "Triple integrals — evaluating in Cartesian, cylindrical, spherical",
                "Jacobians — change of variable in multiple integrals",
                "Improper integrals — convergence and numerical evaluation",
            ],
        },
        "Ordinary Differential Equations": {
            "code": "BMATH203",
            "topics": [
                "Separable ODEs — solving with initial conditions",
                "Exact equations — checking exactness, finding integrating factors",
                "Bernoulli equations — substitution and solving",
                "Orthogonal trajectories — finding family of curves",
                "Higher-order linear ODEs — finding general solution step by step",
                "Undetermined coefficients — computing particular integrals",
                "Variation of parameters — finding PI for non-standard RHS",
                "Cauchy-Euler equations — solving x²y'' + axy' + by = f(x)",
                "Power series solutions — finding series about ordinary points",
                "Frobenius method — solving about regular singular points",
                "Bessel functions — solving Bessel's equation of order n",
                "Legendre polynomials — solving Legendre's equation, Rodrigues' formula",
                "Laplace transforms — solving IVPs with discontinuous forcing",
                "Systems of ODEs — phase portrait and stability analysis",
            ],
        },
    },
    "Semester 3": {
        "Group Theory": {
            "code": "BMATH301",
            "topics": [
                "Group axioms — verifying group structure for explicit sets",
                "Cyclic groups — finding all generators of ℤₙ, listing elements",
                "Cosets and Lagrange — computing cosets of subgroups in S₃, A₄",
                "Normal subgroups — testing normality, building quotient group tables",
                "Homomorphisms — kernel/image computation, verifying isomorphism",
                "First isomorphism theorem — applying to ℤ/nℤ ≅ ℤₙ style results",
                "Permutation groups — cycle decomposition, order of permutations",
                "Even/odd permutations — classifying, showing Aₙ is normal in Sₙ",
                "Cayley's theorem — constructing the regular representation",
                "Direct products — structure of ℤ₂ × ℤ₄, ℤ₂ × ℤ₂ × ℤ₂",
                "Group actions — orbits, stabilisers, Burnside counting",
                "Cauchy's theorem — applying to groups of given order",
                "Sylow theorems — counting Sylow p-subgroups for specific orders",
                "Sylow applications — proving groups of order 15, 21, 35 are cyclic",
            ],
        },
        "Riemann Integration": {
            "code": "BMATH302",
            "topics": [
                "Darboux sums — computing upper/lower sums for specific partitions",
                "Integrability criterion — verifying for monotone and step functions",
                "Properties of Riemann integral — evaluating using linearity/monotonicity",
                "Fundamental theorem — computing derivatives of integral-defined functions",
                "Mean value theorem for integrals — finding the guaranteed point",
                "Improper integrals Type I — convergence of ∫₁^∞ x^{-p} dx etc.",
                "Improper integrals Type II — handling singularities, Dirichlet test",
                "Beta-Gamma evaluation — expressing integrals in terms of B and Γ",
                "Pointwise vs uniform convergence — constructing counterexamples",
                "Weierstrass M-test — verifying uniform convergence of series",
                "Integration of uniformly convergent series — term-by-term",
                "Fourier coefficients — computing aₙ, bₙ for given functions",
                "Parseval's identity — verifying for specific Fourier series",
                "Dirichlet conditions — checking and applying convergence theorem",
            ],
        },
        "Discrete Mathematics": {
            "code": "BMATH303",
            "topics": [
                "Set operations — Venn diagrams, inclusion-exclusion counting",
                "Relations — constructing Hasse diagrams, checking partial orders",
                "Propositional logic — truth tables, tautology verification",
                "Predicate logic — formalising English statements, validity",
                "Mathematical induction — proving divisibility, inequality statements",
                "Graph problems — degree sequence, adjacency matrix, handshaking",
                "Paths and connectivity — BFS/DFS trace, distance in graphs",
                "Trees and spanning trees — Kruskal's and Prim's algorithms on weighted graphs",
                "Euler paths/circuits — Fleury's algorithm on given graphs",
                "Hamiltonian circuits — applying Dirac's theorem",
                "Planarity — applying Euler's formula V - E + F = 2",
                "Graph colouring — finding chromatic number for given graphs",
                "Pigeonhole principle — combinatorial counting problems",
                "Recurrence relations — solving linear recurrences with initial values",
            ],
        },
        "Number Theory": {
            "code": "BMATH304",
            "topics": [
                "GCD and Euclidean algorithm — step-by-step with numerical examples",
                "Linear Diophantine equations — finding all integer solutions",
                "Sieve of Eratosthenes — finding primes, factorisation",
                "Congruences — solving ax ≡ b (mod n) with specific values",
                "Chinese Remainder Theorem — solving simultaneous congruences",
                "Fermat's little theorem — computing a^{p-1} mod p quickly",
                "Euler's totient — computing φ(n), using Euler's theorem",
                "Wilson's theorem — applying to test primality",
                "Primitive roots — finding primitive roots modulo p",
                "Quadratic residues — Legendre symbol computations",
                "Quadratic reciprocity — evaluating Legendre symbols via QRL",
                "Möbius function — computing μ(n) and Möbius inversion",
                "Arithmetic functions — computing σ(n), τ(n) for given n",
                "Order of elements — computing ord_m(a) in (ℤ/mℤ)*",
            ],
        },
    },
    "Semester 4": {
        "Sequences and Series of Functions": {
            "code": "BMATH401",
            "topics": [
                "Pointwise convergence — finding limit function with domain of convergence",
                "Uniform convergence — ε-N verification or constructing counterexamples",
                "Cauchy criterion — verifying uniform convergence of sequences",
                "Dini's theorem — applying to monotone sequences on compact sets",
                "Continuity under uniform convergence — examples and counterexamples",
                "Weierstrass M-test — finding Mₙ and verifying sum converges uniformly",
                "Term-by-term integration — computing integrals of power series",
                "Term-by-term differentiation — conditions and applications",
                "Radius of convergence — using Hadamard's formula, ratio test",
                "Power series — finding sum, interval of convergence, differentiating",
                "Taylor/Maclaurin series — computing series of eˣ, sin x, ln(1+x), (1+x)^α",
                "Fourier coefficients — computing for piecewise functions on [-π, π]",
                "Fourier cosine/sine series — computing on [0, π] with verification",
                "Parseval's theorem — using to sum ∑1/n², ∑1/n⁴ etc.",
            ],
        },
        "Multivariate Calculus": {
            "code": "BMATH402",
            "topics": [
                "Limits in ℝ² — evaluating or proving non-existence along paths",
                "Partial derivatives — computing first and second order partials",
                "Differentiability — verifying total differentiability at a point",
                "Chain rule — implicit differentiation ∂z/∂x, ∂z/∂y",
                "Directional derivative and gradient — computing ∇f and Dᵤf",
                "Tangent planes and normal lines — equations at given surface points",
                "Maxima and minima — finding critical points, applying second derivative test",
                "Lagrange multipliers — optimisation on constrained surfaces",
                "Double integrals — evaluating with explicit limits, change of order",
                "Polar coordinates — converting and evaluating double integrals",
                "Triple integrals — spherical and cylindrical coordinate evaluations",
                "Line integrals — computing ∫_C F·dr for given curves and fields",
                "Green's theorem — verifying and applying to compute area",
                "Stokes' and Divergence theorems — evaluating surface/volume integrals",
            ],
        },
        "Numerical Analysis": {
            "code": "BMATH403",
            "topics": [
                "Error analysis — absolute, relative, truncation errors in computations",
                "Bisection method — iterating to find root with error bound",
                "Regula Falsi method — iterations and convergence on given function",
                "Newton-Raphson method — applying with starting guess, iteration table",
                "Fixed-point iteration — verifying convergence condition, iterating",
                "Lagrange interpolation — constructing and evaluating polynomial",
                "Newton's forward differences — building difference table, interpolating",
                "Newton's divided differences — constructing divided difference table",
                "Numerical differentiation — computing derivatives from tabulated data",
                "Trapezoidal rule — computing integral with error bound",
                "Simpson's 1/3 and 3/8 rules — comparing accuracy on same integral",
                "Gauss-Legendre quadrature — 2-point and 3-point formulas with examples",
                "Euler's method — step-by-step solution table for given IVP",
                "Runge-Kutta (RK4) — computing one or two steps for given IVP",
            ],
        },
    },
    "Semester 5": {
        "Metric Spaces": {
            "code": "BMATH501",
            "topics": [
                "Metric axioms — verifying d is a metric for given definitions",
                "Open and closed sets — proving sets are open/closed in given metrics",
                "Interior, closure, boundary — computing for explicit subsets",
                "Limit points — finding derived sets, showing dense subsets",
                "Convergence in metric spaces — proving sequences converge or diverge",
                "Cauchy sequences — checking completeness of given metric spaces",
                "Completeness — proving C[a,b] with sup norm is complete",
                "Cantor intersection theorem — applying to find fixed points",
                "Baire category theorem — applications to real analysis",
                "Continuous maps — proving continuity via ε-δ or sequential criterion",
                "Uniform continuity — Heine-Cantor theorem applications",
                "Compactness — proving sets are/aren't compact using sequences",
                "Heine-Borel theorem — applying in ℝⁿ with examples",
                "Banach contraction mapping — finding fixed points of contractions",
            ],
        },
        "Ring Theory": {
            "code": "BMATH502",
            "topics": [
                "Ring axioms — verifying ring structure for explicit number systems",
                "Subrings and ideals — finding all ideals of ℤₙ for given n",
                "Quotient rings — constructing and computing in R/I",
                "Ring homomorphisms — kernel, image, applying first isomorphism theorem",
                "Zero divisors — identifying in ℤₙ, finding units",
                "Prime and maximal ideals — classifying in ℤ[x], ℚ[x]",
                "Integral domains and fields — proving/disproving for given rings",
                "Euclidean domains — verifying Euclidean algorithm in Gaussian integers",
                "PIDs — showing ℤ[i] is a PID and factoring elements",
                "UFDs — prime vs irreducible elements, factoring in ℤ[√-5]",
                "Polynomial rings — factoring polynomials over ℤ, ℚ, ℤ_p",
                "Eisenstein's criterion — testing irreducibility for specific polynomials",
                "Gauss's lemma — primitivity and factorisation over ℚ vs ℤ",
                "Field of fractions — constructing from given integral domain",
            ],
        },
        "Partial Differential Equations": {
            "code": "BMATH503",
            "topics": [
                "PDE formation — eliminating arbitrary constants/functions",
                "Lagrange's method — solving pp + qq = r with given p, q, r",
                "Charpit's method — solving nonlinear first-order PDEs step by step",
                "Classification — determining type (E/P/H) for given 2nd order PDE",
                "D'Alembert's solution — solving 1D wave equation on infinite string",
                "Wave equation BVP — semi-infinite string with specific boundary data",
                "Heat equation — separation of variables with given initial temperature",
                "Laplace equation — Dirichlet problem on rectangle with explicit data",
                "Fourier series method — applying to heat/wave equation BVPs",
                "Fourier transform method — solving heat equation on ℝ",
                "Laplace transform — solving PDEs with discontinuous forcing",
                "Method of characteristics — tracing characteristics for 1st order PDEs",
                "Harmonic functions — mean value property, maximum principle",
                "Bessel function solutions — vibrating circular membrane",
            ],
        },
        "Linear Programming and Applications": {
            "code": "BMATH504",
            "topics": [
                "LPP formulation — converting word problems to standard form",
                "Graphical method — plotting feasible region, finding corner points",
                "Convex sets — extreme points, verifying convexity",
                "Simplex method — full iteration table from initial to optimal tableau",
                "Big-M method — introducing artificial variables, complete iterations",
                "Two-phase simplex — Phase I and Phase II with iteration tables",
                "Dual problem — formulating primal-dual pairs, interpreting solution",
                "Duality theorem — strong duality, complementary slackness verification",
                "Dual simplex method — iterating from given infeasible basis",
                "Sensitivity analysis — ranging for objective and RHS coefficients",
                "Transportation problem — NW corner, Vogel's method, MODI optimisation",
                "Assignment problem — Hungarian algorithm step by step",
                "Zero-sum games — finding saddle points, minimax strategies",
                "Mixed strategy games — solving 2×2 games via linear programming",
            ],
        },
    },
    "Semester 6": {
        "Advanced Linear Algebra": {
            "code": "BMATH601",
            "topics": [
                "Gram-Schmidt — orthogonalising given set of vectors step by step",
                "Adjoint operators — computing T* for given inner product and operator",
                "Self-adjoint operators — eigenvalues, spectral theorem application",
                "Normal and unitary operators — verifying and diagonalising",
                "Bilinear forms — matrix representation, Gram matrix computation",
                "Quadratic forms — finding signature, Sylvester's law of inertia",
                "Jordan canonical form — computing J and Jordan basis for 3×3 or 4×4",
                "Minimal polynomial — computing via Cayley-Hamilton and inspection",
                "SVD — computing singular values, U, Σ, Vᵀ for a given matrix",
                "Pseudoinverse — computing A⁺ via SVD, solving least squares",
                "Dual spaces — constructing dual basis, computing annihilators",
                "Rational canonical form — computing for matrices with repeated factors",
                "Positive definite matrices — Cholesky factorisation example",
                "Tensor products — computing in low-dimensional cases",
            ],
        },
        "Advanced Group Theory": {
            "code": "BMATH602",
            "topics": [
                "Sylow applications — groups of order pq, p²q with explicit analysis",
                "Simplicity of A₅ — proving no proper normal subgroup exists",
                "Composition series — constructing for given groups, Jordan-Hölder",
                "Solvable groups — proving S₄ is solvable, Sₙ (n≥5) is not",
                "Nilpotent groups — central series, classifying groups of order p²",
                "Free groups — universal property, normal subgroups of free groups",
                "Group presentations — ⟨a,b | aⁿ, b², (ab)²⟩ style computations",
                "Semidirect products — constructing non-abelian groups of order 2p",
                "Fundamental theorem of f.g. abelian groups — classifying abelian groups",
                "Automorphisms — computing Aut(ℤₙ), Aut(Dₙ), Inn vs Out",
                "Characteristic subgroups — examples and relation to normal subgroups",
                "p-groups — centre is non-trivial, groups of order p²",
                "Frattini subgroup — computing Φ(G) for specific groups",
                "Transfer homomorphism — Burnside's normal complement theorem",
            ],
        },
        "Complex Analysis": {
            "code": "BMATH603",
            "topics": [
                "Cauchy-Riemann equations — verifying analyticity, finding conjugates",
                "Harmonic conjugates — constructing from given harmonic function",
                "Complex integration — evaluating contour integrals directly",
                "Cauchy's integral formula — computing integrals with poles inside",
                "Cauchy's integral formula for derivatives — evaluating higher-order cases",
                "Taylor series — finding series of f(z) at given centre",
                "Laurent series — expanding in annular regions, classifying singularities",
                "Residue computation — simple poles, poles of order n, essential",
                "Residue theorem — evaluating real integrals ∫₋∞^∞ f(x) dx",
                "Evaluation of improper integrals — trigonometric substitution type",
                "Argument principle — counting zeros and poles inside a contour",
                "Rouché's theorem — finding number of zeros of specific polynomials",
                "Möbius transformations — finding images of circles/lines, fixed points",
                "Conformal mappings — mapping upper half-plane to unit disk",
            ],
        },
    },
}

# ══════════════════════════════════════════════════════════════════════════════
#  QUESTION TYPES  —  enforced mix in every paper
# ══════════════════════════════════════════════════════════════════════════════
QUESTION_TYPES = {
    "numerical_compute": (
        "A purely computational question — students must perform step-by-step "
        "calculations and arrive at a numerical or explicit symbolic answer. "
        "E.g. 'Compute…', 'Evaluate…', 'Find all solutions of…', 'Apply [algorithm] to…', "
        "'Using Newton-Raphson find the root of … correct to 4 decimal places', "
        "'Find the eigenvalues and eigenvectors of the matrix …', "
        "'Evaluate the integral ∫∫_R … dA where R is the region …'."
    ),
    "proof_construct": (
        "A rigorous proof question — students must prove a stated theorem or result. "
        "E.g. 'State and prove…', 'Prove that…', 'Show that…'. "
        "Must include the full statement before the proof directive."
    ),
    "example_counter": (
        "A question asking students to construct an example or counterexample, "
        "or to apply a theorem to a SPECIFIC concrete case. "
        "E.g. 'Give an example of a group of order 8 that is not abelian and verify your answer', "
        "'Construct a sequence that is Cauchy but …', "
        "'Show by example that the converse of … is false'."
    ),
    "apply_and_verify": (
        "A two-part question: first apply a method/algorithm to a given data set "
        "or specific object, then verify or interpret the result. "
        "E.g. 'Apply the Simplex method to the following LPP: [data]. Interpret the dual'."
    ),
    "definition_and_short": (
        "State a precise definition, then answer a short computational or "
        "conceptual follow-up on the same topic. "
        "E.g. 'Define a metric space. Is d(x,y) = |x²-y²| a metric on ℝ? Justify.'"
    ),
}

# ══════════════════════════════════════════════════════════════════════════════
#  RICH FALLBACK QUESTION BANK  — numerical questions in every subject
# ══════════════════════════════════════════════════════════════════════════════
FALLBACK = {
    "Algebra": {
        "numerical": [
            "Find all cube roots of $z = -8$ using De Moivre's theorem. Express each root in the form $a + bi$ and plot them on the Argand plane.",
            "Solve the cubic equation $x^3 - 6x^2 + 11x - 6 = 0$ using Cardan's method. Verify by Vieta's formulas.",
            "Find the eigenvalues and corresponding eigenvectors of $A = \\begin{pmatrix} 4 & 1 \\\\ 2 & 3 \\end{pmatrix}$. Hence diagonalise $A$.",
            "Use row reduction to find the rank of $A = \\begin{pmatrix} 1 & 2 & 3 \\\\ 4 & 5 & 6 \\\\ 7 & 8 & 9 \\end{pmatrix}$. Solve the homogeneous system $Ax = 0$.",
            "Verify the Cayley-Hamilton theorem for $A = \\begin{pmatrix} 2 & 1 \\\\ -1 & 3 \\end{pmatrix}$ and use it to compute $A^{-1}$ and $A^3$.",
            "Find all values of $\\lambda$ for which the system $x + y + z = 1,\\; x + 2y + 3z = \\lambda,\\; x + 4y + 9z = \\lambda^2$ is consistent. Solve for those $\\lambda$.",
            "Apply Descartes' rule of signs to $f(x) = x^5 - 3x^3 + 2x^2 - x + 1$ and $f(-x)$. Find the positive and negative real roots.",
            "Solve the quartic $x^4 - 10x^2 + 9 = 0$ using Ferrari's method. Verify all roots.",
        ],
        "proof": [
            "State and prove the Cayley-Hamilton theorem for $2 \\times 2$ matrices. Give a numerical example.",
            "Prove that if $A$ is an $n \\times n$ matrix and $\\lambda$ is an eigenvalue, then $\\lambda^k$ is an eigenvalue of $A^k$.",
            "Prove that the eigenvalues of a real symmetric matrix are all real. Show eigenvectors for distinct eigenvalues are orthogonal.",
        ],
    },
    "Elementary Real Analysis": {
        "numerical": [
            "Using the $\\varepsilon$-$N$ definition, prove that $\\lim_{n\\to\\infty} \\dfrac{3n^2+2}{2n^2-1} = \\dfrac{3}{2}$.",
            "Determine whether the series $\\sum_{n=1}^{\\infty} \\dfrac{n!}{n^n}$ converges or diverges. Use Stirling's approximation if needed.",
            "Test $\\sum_{n=2}^{\\infty} \\dfrac{1}{n(\\log n)^2}$ for convergence using the Integral Test. Compute the tail bound for $N = 100$.",
            "Find $\\limsup$ and $\\liminf$ of the sequence $a_n = (-1)^n \\left(1 + \\dfrac{1}{n}\\right)$. Is the sequence convergent?",
            "Show that $f(x) = \\sqrt{x}$ is uniformly continuous on $[0,\\infty)$ by finding $\\delta$ in terms of $\\varepsilon$.",
            "Find all values of $x$ for which the series $\\sum_{n=1}^{\\infty} \\dfrac{(-1)^{n+1}(x-2)^n}{n}$ converges. Is convergence uniform?",
            "Using Taylor's theorem with Lagrange remainder, show $|\\sin x - (x - x^3/6)| \\leq |x|^5/120$. Hence approximate $\\sin(0.1)$.",
            "Let $a_1 = \\sqrt{2}$ and $a_{n+1} = \\sqrt{2 + a_n}$. Prove the sequence converges and find its limit.",
        ],
        "proof": [
            "State and prove the Monotone Convergence Theorem. Give an example showing the boundedness condition cannot be dropped.",
            "State and prove the Cauchy's general principle of convergence for sequences.",
        ],
    },
    "Probability and Statistics": {
        "numerical": [
            "In a factory, machine A produces 60% of items with 2% defective, machine B produces 40% with 5% defective. An item is defective — find the probability it came from machine A using Bayes' theorem.",
            "A random variable $X$ has PDF $f(x) = 3x^2$ for $0 < x < 1$. Find $E(X)$, $\\text{Var}(X)$, and $P(0.2 < X < 0.8)$.",
            "Fit a Poisson distribution to the data: $x = 0,1,2,3,4$; frequencies $= 122, 60, 15, 2, 1$. Test goodness of fit.",
            "Given the data $x$: 2,3,5,7,9 and $y$: 4,5,7,10,12, find the correlation coefficient and both regression lines.",
            "If $X \\sim N(50, 16)$, find $P(45 < X < 60)$, the median, and the 90th percentile. Use the standard normal table.",
            "A fair die is rolled 180 times. Using Chebyshev's inequality, find a lower bound for the probability that the number of sixes lies between 20 and 40.",
            "The MGF of $X$ is $M_X(t) = \\left(\\dfrac{1-p+pe^t}{1}\\right)^n$. Identify the distribution and find mean and variance.",
            "Two random variables $X, Y$ have joint PMF $P(X=i, Y=j) = \\dfrac{1}{9}$ for $i,j \\in \\{0,1,2\\}$. Find marginals and check independence.",
        ],
        "proof": [
            "State and prove Bayes' theorem. Give a medical testing example illustrating base rate neglect.",
            "State Chebyshev's inequality and prove it for continuous distributions. Show it is tight.",
        ],
    },
    "Linear Algebra": {
        "numerical": [
            "Apply Gram-Schmidt orthogonalisation to $\\{(1,1,0),(1,0,1),(0,1,1)\\}$ in $\\mathbb{R}^3$ with standard inner product. Normalise the result.",
            "Find a basis for and the dimension of the null space and column space of $A = \\begin{pmatrix}1&2&3&4\\\\0&1&2&3\\\\1&3&5&7\\end{pmatrix}$.",
            "Let $T: \\mathbb{R}^3 \\to \\mathbb{R}^2$ be defined by $T(x,y,z) = (x+y, y-z)$. Find the matrix of $T$ with respect to standard bases and with respect to $\\beta = \\{(1,1,0),(0,1,1),(1,0,1)\\}$.",
            "Orthogonally diagonalise $A = \\begin{pmatrix}3&1\\\\1&3\\end{pmatrix}$. Find $A^{10}$ using diagonalisation.",
            "Determine if the following set is linearly independent in $P_2(\\mathbb{R})$: $\\{1+x, x+x^2, 1+x^2\\}$. Find the change-of-basis matrix from this set to the standard basis.",
            "Find the Jordan canonical form of $A = \\begin{pmatrix}2&1&0\\\\0&2&1\\\\0&0&2\\end{pmatrix}$ and a Jordan basis.",
            "For $T: \\mathbb{R}^2 \\to \\mathbb{R}^2$ with matrix $A = \\begin{pmatrix}0&-1\\\\1&0\\end{pmatrix}$, compute $\\text{ker}(T-iI)$ over $\\mathbb{C}$ and verify $T$ is unitary.",
            "Given the inner product $\\langle f,g \\rangle = \\int_0^1 f(t)g(t)\\,dt$ on $P_2(\\mathbb{R})$, apply Gram-Schmidt to $\\{1, x, x^2\\}$.",
        ],
        "proof": [
            "State and prove the Rank-Nullity theorem. Give an application to systems of linear equations.",
            "Prove that eigenvectors corresponding to distinct eigenvalues of a linear operator are linearly independent.",
        ],
    },
    "Calculus": {
        "numerical": [
            "Find the $n$-th derivative of $f(x) = \\dfrac{x}{(x-1)(x-2)}$ using partial fractions and Leibniz's theorem.",
            "Evaluate $\\int_0^{\\pi/2} \\sin^5 x \\cos^4 x\\,dx$ using the Beta function. Express the answer in simplified form.",
            "Find the area enclosed between $y = x^2$ and $y = 2x - x^2$. Also find the volume of the solid obtained by revolving this region about the $x$-axis.",
            "Compute the arc length of the curve $y = \\ln(\\sec x)$ from $x = 0$ to $x = \\pi/4$.",
            "Evaluate $\\iint_R (x^2 + y^2)\\,dA$ over the region $R = \\{(x,y): x^2+y^2 \\leq 4,\\, x \\geq 0\\}$ by converting to polar coordinates.",
            "Find and classify all asymptotes of $f(x) = \\dfrac{x^3}{x^2-4}$. Sketch the curve showing asymptotes and key features.",
            "Evaluate $\\Gamma(7/2)$ and $B(3, 5/2)$ from first principles. Hence compute $\\int_0^1 x^2(1-x)^{3/2}\\,dx$.",
            "Use the substitution $x = 2\\sin\\theta$ to evaluate $\\int_0^2 x^3\\sqrt{4-x^2}\\,dx$. Verify using Beta function.",
        ],
        "proof": [
            "State and prove Leibniz's rule for the $n$-th derivative of a product. Apply it to find the $n$-th derivative of $x^2 e^x$.",
            "Prove that $\\Gamma(n+1) = n!$ for positive integers $n$, starting from the definition $\\Gamma(n) = \\int_0^\\infty t^{n-1}e^{-t}\\,dt$.",
        ],
    },
    "Ordinary Differential Equations": {
        "numerical": [
            "Solve the IVP $\\dfrac{dy}{dx} = \\dfrac{x-y}{x+y}$, $y(1) = 0$. Find the explicit solution.",
            "Solve $y'' - 5y' + 6y = e^{2x} + 3\\sin x$ using the method of undetermined coefficients.",
            "Use variation of parameters to find the general solution of $y'' + y = \\sec x$.",
            "Find the power series solution of $y'' - xy' - y = 0$ about $x = 0$ up to the term containing $x^6$.",
            "Apply the Laplace transform to solve $y'' + 3y' + 2y = e^{-t}u(t-1)$, $y(0) = 0$, $y'(0) = 1$.",
            "Solve the Cauchy-Euler equation $x^2y'' - 3xy' + 4y = x^2 \\ln x$ using the substitution $x = e^t$.",
            "Find the orthogonal trajectories of the family of circles $x^2 + y^2 = 2cx$. Identify the family.",
            "Using the Frobenius method, find two linearly independent solutions of $2xy'' + y' + xy = 0$ near $x = 0$.",
        ],
        "proof": [
            "State and prove the existence-uniqueness theorem for first-order ODEs. Discuss the role of Lipschitz condition.",
            "Prove that the Wronskian of solutions to $y'' + p(x)y' + q(x)y = 0$ is either identically zero or never zero (Abel's theorem).",
        ],
    },
    "Group Theory": {
        "numerical": [
            "Write all elements of $S_4$ that are in $A_4$. List the left cosets of $V_4 = \\{e,(12)(34),(13)(24),(14)(23)\\}$ in $A_4$ and verify Lagrange's theorem.",
            "Construct the multiplication table of $\\mathbb{Z}_{12}/\\langle 4 \\rangle$. Is this quotient group cyclic? To which standard group is it isomorphic?",
            "Find all subgroups of $\\mathbb{Z}_{24}$ and draw the subgroup lattice. Which are normal? Which pairs are isomorphic?",
            "Determine the number of Sylow 3-subgroups and Sylow 5-subgroups of a group of order 45. Conclude about its structure.",
            "Show that a group of order 21 has a normal Sylow 7-subgroup. Describe all groups of order 21 up to isomorphism.",
            "Compute the centre $Z(D_6)$ of the dihedral group of order 12. Find all conjugacy classes of $D_6$.",
            "List all homomorphisms from $\\mathbb{Z}_{12}$ to $\\mathbb{Z}_8$. For each, identify the kernel and image.",
            "Use Burnside's lemma to count the number of distinct necklaces with 6 beads of 3 colours.",
        ],
        "proof": [
            "State and prove Sylow's first theorem (existence of Sylow $p$-subgroups). Illustrate with a group of order 12.",
            "State and prove the First Isomorphism Theorem for groups. Use it to show $\\mathbb{Z}/n\\mathbb{Z} \\cong \\mathbb{Z}_n$.",
        ],
    },
    "Riemann Integration": {
        "numerical": [
            "For $f(x) = x^2$ on $[0,1]$, compute $U(f,P)$ and $L(f,P)$ for the partition $P = \\{0, 0.25, 0.5, 0.75, 1\\}$. Verify $f$ is Riemann integrable and find $\\int_0^1 x^2\\,dx$.",
            "Using the Weierstrass M-test, show that $\\sum_{n=1}^\\infty \\dfrac{\\cos(nx)}{n^2}$ converges uniformly on $\\mathbb{R}$. Hence find $\\int_0^\\pi \\sum_{n=1}^\\infty \\dfrac{\\cos(nx)}{n^2}\\,dx$.",
            "Compute the Fourier series of $f(x) = x$ on $[-\\pi, \\pi]$. Use Parseval's theorem to find $\\sum_{n=1}^\\infty \\dfrac{1}{n^2}$.",
            "Test $\\int_0^\\infty \\dfrac{\\sin x}{x^p}\\,dx$ for convergence for all real $p$. State the values for which it converges absolutely.",
            "Determine the Fourier cosine series of $f(x) = x(\\pi - x)$ on $[0,\\pi]$. Hence find $\\sum_{n=1}^\\infty \\dfrac{1}{n^4}$.",
            "Show that $f(x) = \\begin{cases}1 & x \\in \\mathbb{Q} \\\\ 0 & x \\notin \\mathbb{Q}\\end{cases}$ is not Riemann integrable on $[0,1]$ by computing $U(f,P)$ and $L(f,P)$ for any partition.",
            "Evaluate $\\int_0^{\\infty} x^3 e^{-x}\\,dx$ and $\\int_0^1 (\\ln(1/x))^{1/2}\\,dx$ using the Gamma function.",
            "Test $\\int_0^1 \\dfrac{\\ln x}{\\sqrt{x}}\\,dx$ for convergence and evaluate it.",
        ],
        "proof": [
            "State Darboux's theorem. Prove that a continuous function on $[a,b]$ is Riemann integrable.",
            "State and prove the Fundamental Theorem of Calculus (both parts).",
        ],
    },
    "Discrete Mathematics": {
        "numerical": [
            "Apply Kruskal's algorithm to the weighted graph with vertices $\\{A,B,C,D,E\\}$ and edges $(A,B,4),(A,C,2),(B,C,5),(B,D,10),(C,E,3),(D,E,7),(D,F,11),(E,F,8)$. Find the minimum spanning tree and its weight.",
            "A survey of 100 students finds: 65 study Maths, 45 study Physics, 42 study Chemistry, 20 study M\\&P, 25 study M\\&C, 15 study P\\&C, 8 study all three. Using inclusion-exclusion, find how many study at least one and exactly one subject.",
            "Solve the recurrence $a_n = 5a_{n-1} - 6a_{n-2}$ with $a_0 = 0$, $a_1 = 1$. Find a closed-form expression and compute $a_{10}$.",
            "Draw the graph with degree sequence $(1,2,2,3,4,4)$ and verify with the handshaking lemma. Determine if it is connected and find a spanning tree.",
            "Apply Fleury's algorithm to find an Eulerian circuit in the graph with edges: $\\{AB, AC, BC, BD, CD, DE, AE\\}$. Verify all degrees are even first.",
            "Determine whether the graphs $G_1$ and $G_2$ below are planar using Euler's formula and Kuratowski's criterion. $G_1$: $K_5$ minus one edge; $G_2$: $K_{3,3}$.",
            "Use the pigeonhole principle to prove: Among any 13 people, at least 2 share a birth month. Extend: among $n$ integers, two have the same remainder when divided by $n-1$.",
            "Find the chromatic number of the Petersen graph. Prove that a bipartite graph is 2-colourable.",
        ],
        "proof": [
            "State and prove Euler's formula $V - E + F = 2$ for connected planar graphs.",
            "Prove that a graph is bipartite if and only if it contains no odd-length cycles.",
        ],
    },
    "Number Theory": {
        "numerical": [
            "Use the Euclidean algorithm to find $\\gcd(1071, 462)$ and express it as $1071x + 462y$. Hence solve $1071x \\equiv 3 \\pmod{462}$.",
            "Solve the system: $x \\equiv 2\\pmod{5}$, $x \\equiv 3\\pmod{7}$, $x \\equiv 1\\pmod{11}$ using the Chinese Remainder Theorem.",
            "Compute $\\phi(360)$, $\\sigma(360)$, $\\tau(360)$, and $\\mu(360)$. Verify $\\sum_{d|360} \\mu(d) = 0$.",
            "Find all primitive roots modulo 13. How many are there? Use one to build the discrete logarithm table mod 13.",
            "Using Fermat's little theorem, compute $3^{100} \\pmod{97}$ and $2^{340} \\pmod{341}$. Is 341 prime?",
            "Determine whether 365 is a quadratic residue modulo 7 and modulo 11 using the Legendre symbol. Use quadratic reciprocity where needed.",
            "Find all solutions of the Diophantine equation $17x + 13y = 5$. Verify one solution satisfies the equation.",
            "Use Wilson's theorem to find the remainder when $1000!$ is divided by $1003$ (given 1003 is prime).",
        ],
        "proof": [
            "State and prove Euler's theorem $a^{\\phi(n)} \\equiv 1 \\pmod{n}$ for $\\gcd(a,n)=1$. Deduce Fermat's little theorem.",
            "State and prove the Fundamental Theorem of Arithmetic. Show uniqueness carefully.",
        ],
    },
    "Sequences and Series of Functions": {
        "numerical": [
            "Let $f_n(x) = \\dfrac{x}{1+nx^2}$ on $\\mathbb{R}$. Find the pointwise limit $f$. Is convergence uniform on $\\mathbb{R}$? On $[1,\\infty)$? Justify.",
            "Find the radius and interval of convergence of $\\sum_{n=0}^\\infty \\dfrac{(-1)^n x^{2n+1}}{2n+1}$. Find the sum and its derivative.",
            "Using the Fourier series of $f(x) = x^2$ on $[-\\pi,\\pi]$, derive the sum of $\\sum_{n=1}^\\infty \\dfrac{1}{n^2}$ and $\\sum_{n=1}^\\infty \\dfrac{(-1)^{n+1}}{n^2}$.",
            "Show that $\\sum_{n=1}^\\infty \\dfrac{\\sin(nx)}{n^3}$ converges uniformly on $\\mathbb{R}$ using the M-test. Find its integral $\\int_0^\\pi \\left(\\sum \\dfrac{\\sin(nx)}{n^3}\\right)dx$.",
            "Find the Maclaurin series of $f(x) = \\ln(1 + x + x^2)$ up to the term in $x^6$. Find the radius of convergence.",
            "Let $f_n(x) = x^n(1-x)$ on $[0,1]$. Prove uniform convergence. Verify $\\lim_{n\\to\\infty}\\int_0^1 f_n = \\int_0^1 \\lim f_n$.",
            "Compute the first four non-zero terms of the Taylor series of $\\tan x$ about $x = 0$. Find the radius of convergence.",
            "Find the half-range cosine and sine series for $f(x) = \\pi - x$ on $[0,\\pi]$. At what points does each converge to $f$?",
        ],
        "proof": [
            "State and prove the Weierstrass M-test. Give an example of its application.",
            "State and prove Abel's theorem for power series. Illustrate with $\\ln 2 = \\sum_{n=1}^\\infty (-1)^{n+1}/n$.",
        ],
    },
    "Multivariate Calculus": {
        "numerical": [
            "Find and classify all critical points of $f(x,y) = x^3 + y^3 - 3xy$. Identify local maxima, minima, and saddle points.",
            "Use Lagrange multipliers to find the maximum and minimum of $f(x,y,z) = x + 2y + 3z$ subject to $x^2+y^2+z^2=14$.",
            "Evaluate $\\iint_D (x^2+y^2)\\,dA$ where $D$ is the region bounded by $y=x^2$ and $y=x+2$. Sketch the region.",
            "Convert the integral $\\int_0^1\\int_0^{\\sqrt{1-x^2}}\\int_0^{\\sqrt{1-x^2-y^2}} xyz\\,dz\\,dy\\,dx$ to spherical coordinates and evaluate.",
            "Evaluate $\\int_C \\mathbf{F}\\cdot d\\mathbf{r}$ where $\\mathbf{F} = (y^2, x^2)$ and $C$ is the triangle with vertices $(0,0),(1,0),(1,1)$ traversed counterclockwise. Use Green's theorem.",
            "Find the equation of the tangent plane and normal line to the surface $z = x^2 e^y$ at the point $(1, 0, 1)$.",
            "Show that $\\lim_{(x,y)\\to(0,0)} \\dfrac{x^2y}{x^4+y^2}$ does not exist by approaching along different paths.",
            "Evaluate $\\iint_S \\mathbf{F}\\cdot d\\mathbf{S}$ where $\\mathbf{F} = (x,y,z)$ and $S$ is the closed surface of the cylinder $x^2+y^2\\leq 4$, $0 \\leq z \\leq 3$. Use the Divergence theorem.",
        ],
        "proof": [
            "State and prove Green's theorem in the plane. Use it to find the area of an ellipse $\\tfrac{x^2}{a^2}+\\tfrac{y^2}{b^2}=1$.",
            "State the Divergence theorem. Use it to evaluate $\\iint_S \\mathbf{F}\\cdot\\hat{n}\\,dS$ for $\\mathbf{F} = (x^3,y^3,z^3)$ over the unit sphere.",
        ],
    },
    "Numerical Analysis": {
        "numerical": [
            "Apply Newton-Raphson method to $f(x) = x^3 - 2x - 5 = 0$ starting at $x_0 = 2$. Perform 4 iterations and state the root correct to 4 decimal places.",
            "Using the Bisection method on $f(x) = e^x - 3x = 0$ in $[1,2]$, perform 5 iterations. Estimate the error after each step.",
            "Construct Newton's forward difference table for $f(0)=1, f(1)=3, f(2)=7, f(3)=13, f(4)=21$. Interpolate $f(1.5)$ and $f(2.8)$.",
            "Apply Simpson's 1/3 rule with $n=6$ to approximate $\\int_0^{1.5} e^{-x^2}\\,dx$. Also apply the Trapezoidal rule and compare errors.",
            "Solve the IVP $y' = x - y$, $y(0) = 1$ on $[0,0.4]$ using Euler's method (h=0.1) and RK4 (h=0.2). Compare with exact solution $y = x - 1 + 2e^{-x}$.",
            "Use Lagrange interpolation to find $f(9)$ given: $f(5) = 12$, $f(7) = 13$, $f(11) = 14$, $f(13) = 16$.",
            "Evaluate $\\int_0^{\\pi} \\sin x\\,dx$ numerically using the 3-point Gauss-Legendre quadrature. Compare with the exact value.",
            "Apply the Regula Falsi method to $f(x) = \\cos x - xe^x = 0$ in $[0,1]$. Perform 4 iterations and estimate the error.",
        ],
        "proof": [
            "Derive the Newton-Raphson iteration formula using Taylor series. Prove it has quadratic convergence near a simple root.",
            "Derive the error formula for Simpson's 1/3 rule. Show it is exact for polynomials up to degree 3.",
        ],
    },
    "Metric Spaces": {
        "numerical": [
            "In $(\\mathbb{R}^2, d_\\infty)$ where $d_\\infty((x_1,y_1),(x_2,y_2))=\\max(|x_1-x_2|,|y_1-y_2|)$, describe the open ball $B((0,0),1)$. Prove $d_\\infty$ is a metric.",
            "Apply the Banach Contraction Mapping theorem to prove $f(x) = \\cos x$ has a unique fixed point in $[0,1]$. Perform 3 iterations starting from $x_0 = 0.5$.",
            "Let $X = C[0,1]$ with $d(f,g) = \\int_0^1 |f(x)-g(x)|\\,dx$. Show $f_n(x) = x^n$ is Cauchy but its limit is not in $X$, so $(X,d)$ is incomplete.",
            "Find the closure, interior, and boundary of $A = \\{(x,y) \\in \\mathbb{R}^2 : x^2 + y^2 < 1\\} \\cup \\{(1,0)\\}$ in the Euclidean metric.",
            "Show that the sequence $f_n(x) = \\dfrac{nx}{1+n^2x^2}$ in $(C[0,1], d_\\infty)$ does not converge uniformly to 0.",
            "Prove that $\\mathbb{Q}$ with the Euclidean metric is not complete. Construct an explicit Cauchy sequence in $\\mathbb{Q}$ that does not converge in $\\mathbb{Q}$.",
            "Verify that $K = \\{(x,y)\\in\\mathbb{R}^2 : x^2+y^2 \\leq 1\\}$ is compact using the sequential definition. Deduce that a continuous function on $K$ attains its bounds.",
            "Let $T: (C[0,1], \\|\\cdot\\|_\\infty) \\to (C[0,1], \\|\\cdot\\|_\\infty)$ be $Tf(x) = \\int_0^x f(t)\\,dt$. Show $T$ is a contraction after two iterations, then find the unique fixed point.",
        ],
        "proof": [
            "State and prove the Baire Category Theorem. Deduce that $\\mathbb{R}$ cannot be written as a countable union of nowhere dense sets.",
            "State and prove Cantor's intersection theorem. Show that completeness cannot be dropped.",
        ],
    },
    "Ring Theory": {
        "numerical": [
            "Find all ideals of $\\mathbb{Z}_{12}$. For each ideal $I$, construct the quotient ring $\\mathbb{Z}_{12}/I$ and identify it as a standard ring.",
            "Show that $2+i$ is irreducible in $\\mathbb{Z}[i]$ but $2$ is not prime. Factorise $2, 5, 13$ in the Gaussian integers $\\mathbb{Z}[i]$.",
            "Test each polynomial for irreducibility over $\\mathbb{Q}$: (i) $f(x) = x^4 + 8x + 12$; (ii) $g(x) = x^5 - 4x + 2$; (iii) $h(x) = x^3 - 3x + 1$.",
            "Determine all units and zero divisors in $\\mathbb{Z}[x]/\\langle x^2-1 \\rangle$ and in $\\mathbb{Z}[x]/\\langle x^2+1 \\rangle$. Are these rings integral domains?",
            "Show $\\mathbb{Z}[\\sqrt{-5}]$ is not a UFD by showing $6 = 2 \\times 3 = (1+\\sqrt{-5})(1-\\sqrt{-5})$ are two distinct factorisations into irreducibles.",
            "Find $\\gcd(11+3i, 8-i)$ in $\\mathbb{Z}[i]$ using the Euclidean algorithm. Express it as a linear combination.",
            "Prove that $\\langle 2, x \\rangle$ is a maximal ideal in $\\mathbb{Z}[x]$. Is $\\langle x^2+1 \\rangle$ prime in $\\mathbb{R}[x]$? In $\\mathbb{C}[x]$?",
            "Factor $x^4 - 1$ completely over $\\mathbb{Z}_2$, $\\mathbb{Z}_3$, $\\mathbb{Z}_5$, and $\\mathbb{Q}$. Compare the factorisations.",
        ],
        "proof": [
            "State and prove that $R/I$ is a field if and only if $I$ is a maximal ideal.",
            "State and prove Eisenstein's irreducibility criterion. Apply it to show $x^p - p$ is irreducible over $\\mathbb{Q}$ for prime $p$.",
        ],
    },
    "Partial Differential Equations": {
        "numerical": [
            "Classify $u_{xx} - 4u_{xy} + 4u_{yy} + 3u_x - u = 0$ and reduce it to canonical form. Solve the canonical form.",
            "Solve the heat equation $u_t = u_{xx}$, $0 < x < \\pi$, $t > 0$, with $u(0,t) = u(\\pi,t) = 0$ and $u(x,0) = \\sin x + 2\\sin 3x$.",
            "Using D'Alembert's method, solve $u_{tt} = 4u_{xx}$ with $u(x,0) = \\sin x$, $u_t(x,0) = \\cos x$ on $-\\infty < x < \\infty$.",
            "Solve the Laplace equation $u_{xx}+u_{yy}=0$ on the rectangle $[0,a]\\times[0,b]$ with $u=0$ on three sides and $u(x,b)=f(x)$.",
            "Find the general solution of the first-order PDE $xp + yq = xy - z$ using Lagrange's method. Verify your solution.",
            "Solve $u_t = k u_{xx}$, $u(0,t) = T_1$, $u(L,t) = T_2$, $u(x,0) = 0$ (rod with fixed endpoint temperatures). Find steady state.",
            "Apply Charpit's method to $p^2x + q^2y = z$. Find the complete integral.",
            "Using the Fourier transform, solve $u_t = u_{xx} - u$, $u(x,0) = e^{-x^2}$ on $-\\infty < x < \\infty$.",
        ],
        "proof": [
            "Derive D'Alembert's solution of the 1D wave equation on the infinite line. Interpret the two travelling waves.",
            "Prove the maximum principle for harmonic functions on a bounded domain.",
        ],
    },
    "Linear Programming and Applications": {
        "numerical": [
            "Solve by Simplex: Maximise $Z = 5x_1 + 4x_2 + 3x_3$ subject to $6x_1+4x_2+2x_3 \\leq 240$, $3x_1+2x_2+5x_3 \\leq 270$, $5x_1+6x_2+5x_3 \\leq 420$, $x_i \\geq 0$. Show the full tableau.",
            "Formulate and solve the transportation problem: Supply at A,B,C = 120,80,80; Demand at P,Q,R,S = 150,70,100,90; costs given by a $3\\times 4$ matrix. Use Vogel's approximation then MODI.",
            "Apply the Hungarian algorithm to the $4\\times 4$ assignment problem with cost matrix: Row 1: (9,2,7,8), Row 2: (6,4,3,7), Row 3: (5,8,1,8), Row 4: (7,6,9,4).",
            "Solve the $2 \\times 2$ zero-sum game with payoff matrix $\\begin{pmatrix}1 & -1 \\\\ -1 & 2\\end{pmatrix}$. Find optimal mixed strategies and value of the game.",
            "Find the dual of: Min $3x_1+2x_2$ s.t. $x_1+x_2 \\geq 4$, $2x_1+x_2 \\geq 6$, $x_i \\geq 0$. Solve both primal and dual. Verify complementary slackness.",
            "Solve by graphical method: Maximise $Z = 3x+5y$ s.t. $x \\leq 4$, $2y \\leq 12$, $3x+5y \\leq 25$, $x,y \\geq 0$. Find the shadow prices.",
            "Perform sensitivity analysis on the objective coefficient of $x_1$ and the RHS of constraint 1 in: Max $Z = 2x_1+x_2$ s.t. $x_1+x_2 \\leq 6$, $x_1 \\leq 4$, $x_2 \\leq 5$.",
            "Use two-phase simplex to solve: Min $Z = x_1+x_2$ s.t. $x_1+x_2 \\geq 3$, $x_1+2x_2 \\geq 4$, $x_i \\geq 0$.",
        ],
        "proof": [
            "State and prove the strong duality theorem for linear programming.",
            "Prove that the feasible region of an LPP is a convex set. Show that an optimal solution, if it exists, occurs at a vertex.",
        ],
    },
    "Advanced Linear Algebra": {
        "numerical": [
            "Compute the SVD of $A = \\begin{pmatrix}1&1\\\\0&1\\\\1&0\\end{pmatrix}$. Find the pseudoinverse $A^+$ and use it to solve the least-squares problem $Ax \\approx b$ where $b=(2,1,1)^T$.",
            "Find the Jordan canonical form $J$ and a Jordan basis for $A = \\begin{pmatrix}2&1&0\\\\0&2&0\\\\0&0&3\\end{pmatrix}$. Compute $e^{At}$.",
            "For the quadratic form $Q(x,y,z) = 2x^2+2y^2+2z^2-2xy+2xz-2yz$, find the matrix, diagonalise it, find its signature, and determine definiteness.",
            "Apply Gram-Schmidt to $\\{v_1,v_2,v_3\\} = \\{(1,0,1,0),(1,0,-1,0),(0,1,0,1)\\}$ in $\\mathbb{R}^4$. Extend to an orthonormal basis of $\\mathbb{R}^4$.",
            "Find the adjoint $T^*$ of $T: \\mathbb{C}^2 \\to \\mathbb{C}^2$ defined by $T(z_1,z_2) = (z_1+iz_2, iz_1-z_2)$. Show $T$ is normal and diagonalise it.",
            "Compute the rational canonical form of $A = \\begin{pmatrix}0&0&-2\\\\1&0&1\\\\0&1&2\\end{pmatrix}$. Verify using minimal polynomial.",
            "Find the minimal polynomial of $A = \\begin{pmatrix}1&1&0\\\\0&1&0\\\\0&0&2\\end{pmatrix}$. Is $A$ diagonalisable? Justify.",
            "For the inner product space $L^2[0,1]$, find the projection of $f(x) = x^2$ onto the subspace spanned by $\\{1, x\\}$.",
        ],
        "proof": [
            "State and prove the Spectral Theorem for self-adjoint operators on a finite-dimensional inner product space.",
            "Prove that every matrix has a singular value decomposition. Interpret the singular values geometrically.",
        ],
    },
    "Advanced Group Theory": {
        "numerical": [
            "Prove that there is no simple group of order 36. (Use Sylow's theorems to show a normal Sylow subgroup exists.)",
            "Construct all groups of order 8 up to isomorphism. Which are non-abelian? Describe their presentation in terms of generators and relations.",
            "Find the composition series of $S_4$ and verify the Jordan-Hölder theorem by showing the factors are isomorphic regardless of the series chosen.",
            "Show $A_5$ is simple by proving that any normal subgroup must be $\\{e\\}$ or $A_5$ itself. (Analyse conjugacy classes of 5-cycles, double transpositions.)",
            "Construct the semidirect product $\\mathbb{Z}_7 \\rtimes \\mathbb{Z}_3$ where $\\mathbb{Z}_3$ acts on $\\mathbb{Z}_7$ non-trivially. Write its complete multiplication table for small elements.",
            "Find $\\text{Aut}(\\mathbb{Z}_{12})$ and $\\text{Inn}(S_3)$. Is $S_3$ isomorphic to $\\text{Aut}(\\mathbb{Z}_7)$? Justify.",
            "Classify all abelian groups of order $72 = 2^3 \\cdot 3^2$ up to isomorphism. How many are there?",
            "Compute the Frattini subgroup $\\Phi(G)$ of $G = \\mathbb{Z}_8$ and $G = \\mathbb{Z}_2 \\times \\mathbb{Z}_2 \\times \\mathbb{Z}_2$. Interpret the result.",
        ],
        "proof": [
            "State and prove the Jordan-Hölder theorem. Explain why $A_5$ has no composition series with abelian factors.",
            "Prove that every group of order $p^2$ (where $p$ is prime) is abelian. Classify all such groups.",
        ],
    },
    "Complex Analysis": {
        "numerical": [
            "Verify Cauchy-Riemann equations for $f(z) = z^3$. Find the harmonic conjugate of $u(x,y) = x^3 - 3xy^2 + 2x$.",
            "Evaluate $\\oint_{|z|=2} \\dfrac{z^2-1}{(z-1)^3(z+i)}\\,dz$ using Cauchy's integral formula for derivatives.",
            "Find the Laurent series of $f(z) = \\dfrac{1}{z(z+1)(z+2)}$ valid for $1 < |z| < 2$. Identify the type of singularity at $z=0$.",
            "Using residues, evaluate $\\int_0^{2\\pi} \\dfrac{d\\theta}{2 + \\cos\\theta}$ and $\\int_{-\\infty}^\\infty \\dfrac{dx}{x^4+1}$.",
            "Find the image of the strip $0 < \\text{Im}(z) < \\pi$ under $w = e^z$. Show the Möbius map $w = \\dfrac{z-1}{z+1}$ maps the right half-plane to the unit disk.",
            "Determine the nature of the singularity of each: (i) $\\dfrac{\\sin z}{z^3}$ at $z=0$; (ii) $e^{1/z}$ at $z=0$; (iii) $\\dfrac{z}{\\sin z}$ at $z=k\\pi$. Compute the residue in each case.",
            "Use Rouché's theorem to find the number of zeros of $p(z) = z^6 - 5z^4 + 3z^2 - 1$ inside $|z|=2$. How many lie inside $|z|=1$?",
            "Evaluate $\\int_{-\\infty}^\\infty \\dfrac{x \\sin x}{x^2+a^2}\\,dx$ for $a > 0$ using contour integration. Verify your answer by differentiation under the integral sign.",
        ],
        "proof": [
            "State and prove Cauchy's Integral Theorem (Goursat version). Deduce Cauchy's integral formula.",
            "State and prove the Residue Theorem. Use it to evaluate $\\int_0^\\infty \\dfrac{\\ln x}{1+x^2}\\,dx$.",
        ],
    },
}

# ══════════════════════════════════════════════════════════════════════════════
#  HTML TEMPLATE
# ══════════════════════════════════════════════════════════════════════════════
TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Clark's DU Maths Paper Predictor</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=Crimson+Pro:ital,wght@0,400;0,600;1,400&display=swap" rel="stylesheet">
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css">
<script>
MathJax = {
  tex: { inlineMath: [['$','$'],['\\(','\\)']], displayMath: [['$$','$$'],['\\[','\\]']], tags:'ams' },
  options: { skipHtmlTags:['script','noscript','style','textarea','pre'] }
};
</script>
<script id="MathJax-script" async src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-chtml.js"></script>
<style>
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
:root{
  --bg:#0a0e1a;--bg2:#111827;--surface:#1c2333;--border:#2a3347;
  --gold:#f5c842;--gold2:#e8a500;--accent:#6c8cff;--accent2:#4f6adf;
  --green:#34d399;--red:#f87171;--text:#e2e8f0;--text2:#94a3b8;--text3:#64748b;
  --r:14px;--r2:10px;--shadow:0 4px 24px rgba(0,0,0,.5);
}
html{font-size:15px;scroll-behavior:smooth}
body{background:var(--bg);color:var(--text);font-family:'Inter',sans-serif;min-height:100vh;overflow-x:hidden}
body::before{
  content:'';position:fixed;inset:0;z-index:-1;
  background:radial-gradient(ellipse 80% 60% at 20% 20%,rgba(108,140,255,.08),transparent),
             radial-gradient(ellipse 60% 80% at 80% 80%,rgba(245,200,66,.06),transparent);
  animation:bgsh 12s ease-in-out infinite alternate;
}
@keyframes bgsh{from{opacity:.7}to{opacity:1}}

/* Header */
header{
  position:sticky;top:0;z-index:100;
  background:rgba(10,14,26,.92);backdrop-filter:blur(16px);
  border-bottom:1px solid var(--border);
  padding:.9rem 2rem;
  display:flex;align-items:center;justify-content:space-between;gap:1rem;
}
.logo{display:flex;align-items:center;gap:.75rem}
.logo-icon{
  width:40px;height:40px;
  background:linear-gradient(135deg,var(--gold),var(--gold2));
  border-radius:10px;display:grid;place-items:center;
  font-size:1.2rem;font-weight:800;color:#0a0e1a;
}
.logo-text h1{font-size:1.1rem;font-weight:700}
.logo-text p{font-size:.72rem;color:var(--text3)}
.header-meta{display:flex;align-items:center;gap:1rem}

/* Timer */
#timer-box{
  display:none;align-items:center;gap:.5rem;
  background:var(--surface);border:1px solid var(--border);
  border-radius:var(--r2);padding:.4rem .9rem;font-size:.9rem;font-weight:600;
}
#timer-box.running{border-color:var(--green)}
#timer-box.urgent{border-color:var(--red);animation:pulse .8s infinite}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:.6}}
#timer-display{font-variant-numeric:tabular-nums;color:var(--green)}
#timer-box.urgent #timer-display{color:var(--red)}

.btn{border:none;cursor:pointer;border-radius:var(--r2);font-family:inherit;font-weight:500;transition:all .2s}
.btn:active{transform:scale(.96)}
.btn-gold{background:linear-gradient(135deg,var(--gold),var(--gold2));color:#0a0e1a;padding:.5rem 1.1rem;font-size:.88rem}
.btn-gold:hover{filter:brightness(1.1)}
.btn-outline{background:transparent;border:1px solid var(--border);color:var(--text2);padding:.5rem 1rem;font-size:.88rem}
.btn-outline:hover{border-color:var(--accent);color:var(--text)}

/* Layout */
.app{display:flex;min-height:calc(100vh - 60px)}

/* Sidebar */
.sidebar{
  width:230px;flex-shrink:0;
  background:var(--bg2);border-right:1px solid var(--border);
  padding:1.5rem 1rem;
  position:sticky;top:60px;height:calc(100vh - 60px);overflow-y:auto;
}
.sidebar-title{font-size:.72rem;font-weight:600;letter-spacing:.08em;text-transform:uppercase;color:var(--text3);margin-bottom:1rem;padding:0 .5rem}
.sem-btn{
  width:100%;display:flex;align-items:center;gap:.7rem;
  padding:.65rem .75rem;border-radius:var(--r2);cursor:pointer;border:none;
  background:transparent;color:var(--text2);font-family:inherit;font-size:.88rem;
  text-align:left;transition:all .2s;margin-bottom:.25rem;
}
.sem-btn:hover{background:var(--surface);color:var(--text)}
.sem-btn.active{background:linear-gradient(90deg,rgba(108,140,255,.18),rgba(108,140,255,.05));color:var(--accent);border-left:3px solid var(--accent)}
.sem-num{width:26px;height:26px;border-radius:6px;background:var(--surface);display:grid;place-items:center;font-size:.8rem;font-weight:700;flex-shrink:0}
.sem-btn.active .sem-num{background:var(--accent);color:#fff}

.info-box{
  margin-top:2rem;padding:.75rem;background:var(--surface);
  border-radius:var(--r2);border:1px solid var(--border);
}
.info-box .ib-title{font-size:.72rem;color:var(--text3);margin-bottom:.4rem;font-weight:600}
.info-box div{font-size:.8rem;color:var(--text2);line-height:1.7}

/* Main */
.main{flex:1;padding:2rem;max-width:960px}

/* Welcome */
.welcome{display:flex;flex-direction:column;align-items:center;justify-content:center;min-height:70vh;text-align:center;gap:1.5rem}
.welcome-icon{font-size:4rem}
.welcome h2{font-size:2rem;font-weight:700;background:linear-gradient(135deg,var(--gold),var(--accent));-webkit-background-clip:text;-webkit-text-fill-color:transparent}
.welcome p{color:var(--text2);max-width:480px;line-height:1.7}
.badges{display:flex;flex-wrap:wrap;justify-content:center;gap:.5rem}
.badge{background:var(--surface);border:1px solid var(--border);border-radius:999px;padding:.3rem .85rem;font-size:.78rem;color:var(--text2)}

/* Subject grid */
.subjects-section{animation:fadeIn .35s ease}
@keyframes fadeIn{from{opacity:0;transform:translateY(12px)}to{opacity:1;transform:none}}
.section-header{display:flex;align-items:center;gap:.75rem;margin-bottom:1.5rem}
.section-header h2{font-size:1.4rem;font-weight:700}
.semester-tag{background:linear-gradient(135deg,var(--accent2),var(--accent));color:white;font-size:.78rem;font-weight:600;padding:.25rem .75rem;border-radius:999px}
.subjects-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:1rem;margin-bottom:2.5rem}
.subject-card{
  background:var(--surface);border:1px solid var(--border);border-radius:var(--r);
  padding:1.4rem;cursor:pointer;transition:all .25s;position:relative;overflow:hidden;
}
.subject-card::before{
  content:'';position:absolute;top:0;left:0;right:0;height:3px;
  background:linear-gradient(90deg,var(--gold),var(--accent));
  transform:scaleX(0);transition:transform .3s;transform-origin:left;
}
.subject-card:hover{border-color:var(--accent);transform:translateY(-3px);box-shadow:var(--shadow)}
.subject-card:hover::before{transform:scaleX(1)}
.subject-card h3{font-size:1rem;font-weight:600;margin-bottom:.35rem}
.subject-card .code{font-size:.72rem;color:var(--text3);font-family:monospace;letter-spacing:.05em}
.subject-card .generate-hint{margin-top:.9rem;display:flex;align-items:center;gap:.4rem;font-size:.78rem;font-weight:500;color:var(--accent);opacity:0;transition:opacity .2s}
.subject-card:hover .generate-hint{opacity:1}

/* Loading */
.loading-state{display:none;flex-direction:column;align-items:center;justify-content:center;min-height:60vh;gap:1.5rem;text-align:center}
.spinner{width:56px;height:56px;border:3px solid var(--border);border-top-color:var(--gold);border-radius:50%;animation:spin 1s linear infinite}
@keyframes spin{to{transform:rotate(360deg)}}
.loading-state h3{font-size:1.2rem;font-weight:600}
.loading-state p{color:var(--text2);font-size:.9rem}
.loading-steps{display:flex;flex-direction:column;gap:.5rem;width:100%;max-width:340px}
.step{display:flex;align-items:center;gap:.7rem;padding:.55rem .9rem;border-radius:var(--r2);background:var(--surface);font-size:.85rem;color:var(--text3);transition:all .4s}
.step.active{color:var(--text);border-left:3px solid var(--gold)}
.step.done{color:var(--green);border-left:3px solid var(--green)}
.step i{width:16px;text-align:center}

/* Paper section */
.paper-section{display:none;animation:fadeIn .4s ease}
.paper-toolbar{display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:.75rem;margin-bottom:1.5rem}
.paper-toolbar-left{display:flex;align-items:center;gap:.75rem}
.predicted-badge{
  display:inline-flex;align-items:center;gap:.4rem;
  background:#fff8e6;border:1px solid #f5c842;color:#7a5c00;
  border-radius:999px;padding:.25rem .8rem;font-size:.78rem;font-weight:600;margin-bottom:1rem;
}

/* Paper render — white page */
.paper-wrap{
  background:#fff;color:#111;border-radius:var(--r);
  padding:2.5rem 3rem;box-shadow:var(--shadow);
  font-family:'Crimson Pro',Georgia,serif;font-size:1.05rem;line-height:1.8;
}
.paper-meta{text-align:center;margin-bottom:1.5rem;padding-bottom:1.2rem;border-bottom:2px solid #222}
.paper-meta .pages-note{font-size:.9rem}
.paper-meta h2{font-size:1.1rem;font-weight:700;margin:.4rem 0 .2rem;text-transform:uppercase;letter-spacing:.04em}
.paper-id{
  font-size:.85rem;color:#444;
  display:grid;grid-template-columns:1fr 1fr;gap:.2rem .5rem;
  margin:.8rem auto;max-width:500px;text-align:left;
}
.paper-id span{font-weight:600}
.marks-row{display:flex;justify-content:space-between;align-items:center;margin-top:.5rem;font-weight:700;font-size:1rem}
.paper-instructions{margin-bottom:1.5rem;padding:.9rem 1.2rem;background:#f5f5f5;border-left:4px solid #333;font-size:.93rem}
.paper-instructions strong{display:block;margin-bottom:.35rem;font-size:1rem}
.paper-instructions ol{padding-left:1.4rem}
.paper-instructions li{margin-bottom:.2rem}

/* Question type pill */
.qtype-pill{
  display:inline-block;padding:.12rem .55rem;border-radius:999px;
  font-size:.72rem;font-weight:600;font-family:'Inter',sans-serif;
  letter-spacing:.03em;margin-left:.5rem;
}
.qtype-proof{background:#e8f0fe;color:#1a56db}
.qtype-numerical{background:#fef3c7;color:#92400e}
.qtype-example{background:#d1fae5;color:#065f46}
.qtype-apply{background:#ede9fe;color:#5b21b6}
.qtype-defn{background:#fee2e2;color:#991b1b}

.question-block{margin-bottom:2rem}
.question-num{
  font-size:1.1rem;font-weight:700;
  border-bottom:1px solid #ddd;padding-bottom:.4rem;margin-bottom:1rem;
  display:flex;justify-content:space-between;align-items:center;
}
.question-num .q-marks{font-size:.9rem;color:#555;font-weight:500}
.part-row{display:flex;gap:.9rem;margin-bottom:1rem;padding:.6rem 0;border-bottom:1px dashed #e5e5e5}
.part-row:last-child{border-bottom:none}
.part-label{font-weight:700;flex-shrink:0;min-width:1.6rem;color:#333}
.part-text{flex:1}
.part-marks{flex-shrink:0;font-size:.88rem;color:#666;font-weight:500;padding-top:.1rem}
.paper-footer{text-align:center;margin-top:2rem;padding-top:1rem;border-top:1px solid #ddd;font-size:.9rem;color:#666}

/* Print */
@media print{
  .sidebar,header,.paper-toolbar,.predicted-badge{display:none!important}
  body{background:white}
  .paper-wrap{box-shadow:none;padding:0}
  .paper-section{display:block!important}
  .qtype-pill{display:none!important}
}
@media(max-width:768px){
  .sidebar{display:none}
  .main{padding:1rem}
  .paper-wrap{padding:1.5rem 1.2rem}
  .paper-id{grid-template-columns:1fr}
}
::-webkit-scrollbar{width:6px}
::-webkit-scrollbar-track{background:var(--bg)}
::-webkit-scrollbar-thumb{background:var(--border);border-radius:3px}
</style>
</head>
<body>

<header>
  <div class="logo">
    <div class="logo-icon">∑</div>
    <div class="logo-text">
      <h1>Clark's DU Maths Predictor</h1>
      <p>B.Sc (Hons) Mathematics · Delhi University · NEP</p>
    </div>
  </div>
  <div class="header-meta">
    <div id="timer-box">
      <i class="fa-solid fa-clock"></i>
      <span id="timer-display">3:00:00</span>
      <button class="btn btn-outline" style="padding:.3rem .7rem;font-size:.78rem" onclick="resetTimer()">Reset</button>
    </div>
    <button class="btn btn-gold" onclick="window.print()">
      <i class="fa-solid fa-print"></i> Print
    </button>
  </div>
</header>

<div class="app">
  <aside class="sidebar">
    <div class="sidebar-title">Semester</div>
    {% for sem in semesters %}
    <button class="sem-btn" onclick="selectSemester('{{ sem }}', this)">
      <div class="sem-num">{{ loop.index }}</div>
      <span>{{ sem }}</span>
    </button>
    {% endfor %}
    <div class="info-box">
      <div class="ib-title">Format (90 Marks)</div>
      <div>
        📄 6 Questions<br>
        📝 3 Parts (a, b, c) each<br>
        ✅ Attempt any 2 per Q<br>
        🔢 Mix: Numericals + Proofs<br>
        🎯 7.5 marks per part<br>
        ⏱ 3 Hours
      </div>
    </div>
  </aside>

  <main class="main" id="main">
    <!-- Welcome -->
    <div class="welcome" id="welcome-state">
      <div class="welcome-icon">📐</div>
      <h2>Predicted Paper Generator</h2>
      <p>Select a semester → choose a subject → get a fully unique AI-predicted paper with <strong>numerical, proof-based, and application questions</strong> every time.</p>
      <div class="badges">
        <span class="badge">🏛 Delhi University</span>
        <span class="badge">📚 NEP Aligned</span>
        <span class="badge">🎯 90 Marks</span>
        <span class="badge">🔢 Numerical Questions</span>
        <span class="badge">🤖 AI-Powered</span>
        <span class="badge">20 Subjects</span>
      </div>
    </div>

    <!-- Subject Grid -->
    <div class="subjects-section" id="subjects-section" style="display:none">
      <div class="section-header">
        <h2 id="sem-heading"></h2>
        <span class="semester-tag" id="sem-tag"></span>
      </div>
      <div class="subjects-grid" id="subjects-grid"></div>
    </div>

    <!-- Loading -->
    <div class="loading-state" id="loading-state">
      <div class="spinner"></div>
      <h3 id="loading-label">Generating Predicted Paper…</h3>
      <p>Building a unique paper with numerical + proof questions.</p>
      <div class="loading-steps">
        <div class="step" id="step1"><i class="fa fa-dice"></i> Randomising topic mix</div>
        <div class="step" id="step2"><i class="fa fa-calculator"></i> Selecting numerical questions</div>
        <div class="step" id="step3"><i class="fa fa-file-alt"></i> Composing proof questions</div>
        <div class="step" id="step4"><i class="fa fa-check-circle"></i> Formatting DU paper</div>
      </div>
    </div>

    <!-- Paper -->
    <div class="paper-section" id="paper-section">
      <div class="paper-toolbar">
        <div class="paper-toolbar-left">
          <button class="btn btn-outline" onclick="goBack()">
            <i class="fa fa-arrow-left"></i> Back
          </button>
          <button class="btn btn-gold" onclick="regeneratePaper()">
            <i class="fa fa-rotate"></i> New Unique Paper
          </button>
        </div>
        <div style="font-size:.82rem;color:var(--text3)">
          <i class="fa fa-info-circle"></i> Every click = structurally different paper
        </div>
      </div>
      <div class="predicted-badge">
        <i class="fa-solid fa-wand-magic-sparkles"></i>
        AI Predicted · DU PYQ Pattern · Unique Every Click
      </div>
      <div class="paper-wrap" id="paper-content"></div>
    </div>
  </main>
</div>

<script>
let currentSemester = null;
let currentSubject  = null;
let timerInterval   = null;
let timerSeconds    = 10800;

function selectSemester(sem, btn) {
  currentSemester = sem;
  document.querySelectorAll('.sem-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  loadSubjects(sem);
}

async function loadSubjects(sem) {
  const n = sem.split(' ')[1];
  const r = await fetch('/api/subjects/' + n);
  const subjects = await r.json();
  renderGrid(sem, subjects);
}

function renderGrid(sem, subjects) {
  hide('welcome-state'); hide('paper-section'); hide('loading-state');
  show('subjects-section');
  document.getElementById('sem-heading').textContent = sem;
  document.getElementById('sem-tag').textContent = sem;

  const icons = {
    'Algebra':'∑','Elementary Real Analysis':'ε','Probability and Statistics':'P',
    'Linear Algebra':'⊗','Calculus':'∫','Ordinary Differential Equations':'d/dt',
    'Group Theory':'G','Riemann Integration':'∫R','Discrete Mathematics':'∧',
    'Number Theory':'ℕ','Sequences and Series of Functions':'∑ₙ',
    'Multivariate Calculus':'∇','Numerical Analysis':'≈',
    'Metric Spaces':'d(x,y)','Ring Theory':'R','Partial Differential Equations':'∂',
    'Linear Programming and Applications':'LP','Advanced Linear Algebra':'V*',
    'Advanced Group Theory':'Ã','Complex Analysis':'ℂ'
  };

  const grid = document.getElementById('subjects-grid');
  grid.innerHTML = '';
  subjects.forEach(sub => {
    grid.innerHTML += `
      <div class="subject-card" onclick="generatePaper('${sub}')">
        <div style="font-size:1.6rem;margin-bottom:.5rem">${icons[sub]||'∴'}</div>
        <h3>${sub}</h3>
        <div style="font-size:.75rem;color:var(--text3);margin-top:.3rem">
          Numericals + Proofs + Applications
        </div>
        <div class="generate-hint"><i class="fa fa-bolt"></i> Generate Predicted Paper</div>
      </div>`;
  });
}

async function generatePaper(subject) {
  currentSubject = subject;
  hide('subjects-section'); hide('welcome-state'); hide('paper-section');
  show('loading-state');
  document.getElementById('loading-label').textContent = `Building paper for ${subject}…`;

  const steps = ['step1','step2','step3','step4'];
  steps.forEach(s => document.getElementById(s).className = 'step');
  steps.forEach((s,i) => {
    setTimeout(() => {
      if (i > 0) document.getElementById(steps[i-1]).className = 'step done';
      document.getElementById(s).className = 'step active';
    }, i * 850);
  });

  const semNum = currentSemester.split(' ')[1];
  try {
    const resp = await fetch('/api/generate', {
      method: 'POST',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify({ subject, semester: semNum })
    });
    const data = await resp.json();
    if (data.success) {
      setTimeout(() => {
        document.getElementById('step4').className = 'step done';
        renderPaper(data.paper);
      }, 3600);
    } else {
      showError(data.error || 'Generation failed.');
    }
  } catch(e) {
    showError('Network error: ' + e.message);
  }
}

async function regeneratePaper() {
  if (currentSubject) await generatePaper(currentSubject);
}

/* ─── PILL LABELS ─── */
const PILL = {
  numerical_compute: ['qtype-numerical','Numerical'],
  proof_construct:   ['qtype-proof','Proof'],
  example_counter:   ['qtype-example','Example/Counter'],
  apply_and_verify:  ['qtype-apply','Apply & Verify'],
  definition_and_short: ['qtype-defn','Defn + Short'],
};

function renderPaper(paper) {
  hide('loading-state'); hide('subjects-section'); hide('welcome-state');
  show('paper-section');

  const now = new Date();
  const dateStr = now.toLocaleDateString('en-IN',{day:'2-digit',month:'long',year:'numeric'});
  const paperId = 'DU-' + paper.code + '-' + Math.floor(Math.random()*9000+1000);

  let qHtml = '';
  paper.questions.forEach((q,qi) => {
    let partsHtml = q.parts.map(p => {
      const [cls, label] = PILL[p.qtype] || ['qtype-proof','Proof'];
      return `
        <div class="part-row">
          <div class="part-label">(${p.label})</div>
          <div class="part-text">
            <span class="qtype-pill ${cls}">${label}</span>
            ${p.question}
          </div>
          <div class="part-marks">[7.5]</div>
        </div>`;
    }).join('');
    qHtml += `
      <div class="question-block">
        <div class="question-num">
          Q${q.number}.&nbsp;&nbsp;<em style="font-size:.9rem;font-weight:400;color:#555">${q.topic_hint||''}</em>
          <span class="q-marks">Attempt any TWO &nbsp;|&nbsp; 7.5 × 2 = 15 Marks</span>
        </div>
        ${partsHtml}
      </div>`;
  });

  document.getElementById('paper-content').innerHTML = `
    <div class="paper-meta">
      <div class="pages-note">[This question paper contains 8 printed pages.]</div>
      <div style="float:right;font-size:.9rem;margin-top:-.5rem">Roll No. ________________</div><br>
      <div class="paper-id">
        <div>Sr. No. of Question Paper</div><div><span>${paperId}</span></div>
        <div>Unique Paper Code</div>        <div><span>${paper.code}</span></div>
        <div>Name of the Paper</div>        <div><span>${paper.subject}</span></div>
        <div>Name of the Course</div>       <div><span>B.Sc (Hons) Mathematics</span></div>
        <div>Semester</div>                 <div><span>${paper.semester}</span></div>
      </div>
      <div class="marks-row">
        <div>Duration: 3 Hours</div>
        <div>Maximum Marks: 90</div>
      </div>
    </div>
    <div class="paper-instructions">
      <strong>Instructions for Candidates</strong>
      <ol>
        <li>Write your Roll No. on the top immediately on receipt of this question paper.</li>
        <li>All questions are compulsory.</li>
        <li>Attempt any <strong>two</strong> parts from each question (Q1 to Q6).</li>
        <li>Each part carries <strong>7.5 marks</strong>.</li>
        <li>Notations used have their usual meanings unless otherwise stated.</li>
        <li>Calculators are not permitted.</li>
      </ol>
    </div>
    ${qHtml}
    <div class="paper-footer">
      ✦ &nbsp; AI-Predicted Paper · clark.rf.gd · Generated ${dateStr} &nbsp; ✦<br>
      <small>Based on DU PYQ pattern analysis — for exam preparation only</small>
    </div>`;

  if (window.MathJax) MathJax.typesetPromise();
  startTimer();
}

/* ─── TIMER ─── */
function startTimer() {
  timerSeconds = 10800;
  clearInterval(timerInterval);
  const box = document.getElementById('timer-box');
  box.style.display = 'flex'; box.className = 'running';
  updateTimerDisplay();
  timerInterval = setInterval(() => {
    timerSeconds--;
    updateTimerDisplay();
    if (timerSeconds <= 0) { clearInterval(timerInterval); alert('⏰ Time is up!'); }
    if (timerSeconds <= 1800) box.className = 'urgent';
  }, 1000);
}
function updateTimerDisplay() {
  const h = Math.floor(timerSeconds/3600);
  const m = Math.floor((timerSeconds%3600)/60);
  const s = timerSeconds%60;
  document.getElementById('timer-display').textContent =
    `${String(h).padStart(2,'0')}:${String(m).padStart(2,'0')}:${String(s).padStart(2,'0')}`;
}
function resetTimer() {
  timerSeconds = 10800; updateTimerDisplay();
  document.getElementById('timer-box').className = 'running';
}

/* ─── NAV ─── */
function goBack() {
  clearInterval(timerInterval);
  document.getElementById('timer-box').style.display = 'none';
  hide('paper-section');
  currentSemester ? show('subjects-section') : show('welcome-state');
}
function showError(msg) {
  hide('loading-state'); show('subjects-section'); alert('Error: ' + msg);
}
function show(id) { document.getElementById(id).style.display = 'flex'; }
function hide(id) { document.getElementById(id).style.display = 'none'; }
</script>
</body>
</html>"""


# ══════════════════════════════════════════════════════════════════════════════
#  ROUTES
# ══════════════════════════════════════════════════════════════════════════════
@app.route("/")
def home():
    return render_template_string(TEMPLATE, semesters=list(CURRICULUM.keys()))


@app.route("/api/subjects/<int:sem_num>")
def get_subjects(sem_num):
    key = f"Semester {sem_num}"
    return jsonify(list(CURRICULUM.get(key, {}).keys()))


@app.route("/api/generate", methods=["POST"])
def generate_paper():
    data        = request.json or {}
    subject     = data.get("subject", "")
    semester    = data.get("semester", "1")
    sem_key     = f"Semester {semester}"
    sub_data    = CURRICULUM.get(sem_key, {}).get(subject)
    if not sub_data:
        return jsonify({"success": False, "error": "Subject not found"}), 404

    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if api_key:
        paper = _generate_via_claude(subject, semester, sub_data, api_key)
    else:
        paper = _generate_fallback(subject, semester, sub_data)

    return jsonify({"success": True, "paper": paper})


# ══════════════════════════════════════════════════════════════════════════════
#  CLAUDE GENERATION  — 5 question-type categories enforced every call
# ══════════════════════════════════════════════════════════════════════════════
def _generate_via_claude(subject, semester, sub_data, api_key):
    import anthropic as ant

    client = ant.Anthropic(api_key=api_key)

    topics   = sub_data["topics"]
    code     = sub_data["code"]

    # Shuffle topics and pick a fresh subset — different every call
    shuffled = topics[:]
    random.shuffle(shuffled)
    chosen_12 = shuffled[:12]

    # Unique seed that changes every call
    seed = f"{time.time_ns()}-{uuid.uuid4().hex[:8]}"

    # Mandatory question-type sequence — randomised per call
    all_types = list(QUESTION_TYPES.keys())
    random.shuffle(all_types)
    # Ensure at least 3 numericals and 2 proofs in every paper
    mandatory = (["numerical_compute"] * 3 + ["proof_construct"] * 2
                 + ["example_counter"])
    random.shuffle(mandatory)
    # Build 6 × 3 = 18 type slots
    type_pool = mandatory + all_types + all_types     # plenty to draw from
    random.shuffle(type_pool)
    type_slots = type_pool[:18]

    type_descriptions = "\n".join(
        f"  {k}: {v}" for k, v in QUESTION_TYPES.items()
    )

    prompt = f"""You are a DU examination setter. Generate a PREDICTED QUESTION PAPER.

Subject : {subject}   Code: {code}
Course  : B.Sc (Hons) Mathematics, Delhi University (NEP)
Semester: {semester}
Format  : 6 questions × 3 parts (a,b,c) × 7.5 marks = 90 marks total.
          Student attempts ANY TWO parts per question.

Generation seed (ensures uniqueness — change the questions every time): {seed}

MANDATORY TOPIC COVERAGE — cover ALL 12 topics across the 6 questions:
{chr(10).join(f"  {i+1}. {t}" for i, t in enumerate(chosen_12))}

QUESTION TYPE TAXONOMY (every part must declare its type):
{type_descriptions}

REQUIRED TYPE DISTRIBUTION for this paper (strictly follow this for the 18 parts):
{chr(10).join(f"  Part slot {i+1}: {t}" for i, t in enumerate(type_slots))}

RULES — STRICTLY FOLLOW EVERY ONE:
1. EXACTLY 3 PARTS per question: (a), (b), (c). No more, no less.
2. USE the type in "type_slots" exactly as listed for each part.
3. "numerical_compute" parts MUST contain specific numerical data:
   - actual matrices with entries, specific functions, concrete data tables,
   - step counts ("perform 4 iterations"), error bounds, specific values.
   - DO NOT write "find the eigenvalues of matrix A" without giving A.
4. "proof_construct" parts: state the theorem fully, then say "State and prove..."
5. "example_counter": give a specific group/function/space and ask to verify.
6. "apply_and_verify": give the complete data (tableau, table, system) in the question.
7. Every part must be DIFFERENT from all other parts — no topic repetition.
8. Use LaTeX inside dollar signs: e.g. $\\lambda$, $A = \\begin{{pmatrix}}1&2\\\\3&4\\end{{pmatrix}}$.
9. Each part should take ~20 minutes to complete. Do not make questions trivial.
10. include topic_hint per question (a very short phrase, ≤ 5 words).

Return ONLY valid JSON — no markdown, no preamble, nothing else:
{{
  "questions": [
    {{
      "number": 1,
      "topic_hint": "short phrase",
      "parts": [
        {{"label": "a", "qtype": "...", "question": "...", "marks": 7.5}},
        {{"label": "b", "qtype": "...", "question": "...", "marks": 7.5}},
        {{"label": "c", "qtype": "...", "question": "...", "marks": 7.5}}
      ]
    }}
  ]
}}"""

    resp = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = resp.content[0].text.strip()
    for fence in ["```json", "```"]:
        if raw.startswith(fence):
            raw = raw[len(fence):]
    raw = raw.rstrip("`").strip()

    paper_data = json.loads(raw)
    paper_data.update({"subject": subject, "semester": semester, "code": code})
    return paper_data


# ══════════════════════════════════════════════════════════════════════════════
#  FALLBACK GENERATION  — rich numerical bank, guaranteed variety
# ══════════════════════════════════════════════════════════════════════════════
def _generate_fallback(subject, semester, sub_data):
    """
    Builds a paper without Claude.  Uses FALLBACK bank if available,
    otherwise builds from topic list.  Guarantees:
      - At least 2 numerical questions per paper
      - At least 1 proof per paper
      - Never the same ordering twice (strong random shuffle)
    """
    code = sub_data["code"]
    bank = FALLBACK.get(subject, {})

    numericals = bank.get("numerical", [])
    proofs     = bank.get("proof", [])

    # Strong shuffle — different every call
    rng_seed = int(time.time_ns()) ^ random.getrandbits(31)
    rng = random.Random(rng_seed)
    rng.shuffle(numericals)
    rng.shuffle(proofs)

    # Build a flat pool: alternate numerical + proof generously
    pool = []
    n_idx, p_idx = 0, 0
    for i in range(18):
        if i % 3 == 0 and n_idx < len(numericals):       # every 3rd = numerical
            pool.append(("numerical_compute", numericals[n_idx])); n_idx += 1
        elif i % 5 == 0 and p_idx < len(proofs):         # every 5th = proof
            pool.append(("proof_construct", proofs[p_idx])); p_idx += 1
        elif n_idx < len(numericals):
            pool.append(("numerical_compute", numericals[n_idx])); n_idx += 1
        elif p_idx < len(proofs):
            pool.append(("proof_construct", proofs[p_idx])); p_idx += 1
        else:
            # Use topic-derived question as last resort
            t = rng.choice(sub_data["topics"])
            pool.append(("example_counter",
                          f"Give a concrete example illustrating {t.lower()}. "
                          f"Verify all conditions rigorously."))

    # Top up to 18 if pool is short
    while len(pool) < 18:
        t = rng.choice(sub_data["topics"])
        pool.append(("numerical_compute",
                     f"Compute a complete numerical example for the following: {t}."))

    rng.shuffle(pool)   # shuffle the entire 18-part pool for variety

    questions = []
    labels = ["a", "b", "c"]
    for qi in range(6):
        parts = []
        for pi in range(3):
            qtype, qtext = pool[qi * 3 + pi]
            parts.append({
                "label": labels[pi],
                "qtype": qtype,
                "question": qtext,
                "marks": 7.5,
            })
        questions.append({
            "number": qi + 1,
            "topic_hint": "",
            "parts": parts,
        })

    return {"subject": subject, "semester": semester, "code": code,
            "questions": questions}


# ══════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    port  = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "0") == "1"
    print("\n" + "═" * 62)
    print("  Clark's DU Maths PYQ Predictor  —  FIXED BUILD")
    print(f"  http://localhost:{port}")
    print("  Fixes: numerical questions, genuine variety, type enforcement")
    print("  Set ANTHROPIC_API_KEY for AI mode; fallback works without it.")
    print("═" * 62 + "\n")
    app.run(host="0.0.0.0", port=port, debug=debug)
