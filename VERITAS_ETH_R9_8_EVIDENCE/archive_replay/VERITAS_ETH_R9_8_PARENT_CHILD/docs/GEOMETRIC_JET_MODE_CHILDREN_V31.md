# v3.1 Exact geometric extension-ring modes and finite scalar children

## Mathematical construction

Given an independently verified finite D.3 packing, choose an interpolation node `t` with `i=v2(t)<a`, tile width `B=2^(i+1)`, and `T=t+2L V`. For any cross-group row/column pair in the same packet, the column index has form `y=y0+B*j`. The Cauchy kernel admits the geometric expansion

`W[x,y](T) = sum_{b>=0} A[x,y0,b](T) * j^b`,

`A[x,y0,b](T) = W[x,y0](T) * (B/(T-y0+x))^b`.

The reference calculates truncated rational Taylor coefficients before mapping them to the 2-adic extension ring. This avoids illegally inverting even integers modulo `2^p`. Each coefficient is independently checked to be 2-adically integral, and every mode is assigned its **measured** minimum valuation. Only terms whose sum of certified mode weights is less than `p` are retained. Full Cauchy jets are reconstructed and checked against independently computed matrix entries.

## Mode-indexed finite child scalar identity

Expand each deformed row factor in formal mode variables. Group-local polynomials contain original row and column factors, local Cauchy interactions and source/target mode factors. For each retained exponent vector beta, evaluate exact scalar children independently on each symbol group; multiply these child results and sum over beta. The result is cross-checked against the original `4^M` half-edge enumeration of the Cauchy network. This removes the global boundary enumeration used in v3.0, but may cost more work on tiny examples.

## Limitations

- The children are finite scalar reference calculations, not the paper's implicit lower-size recursively constructed packet tensors.
- No `M_child <= M/8` claim, no finite-size speedup claim, and no subexponential runtime theorem.
- The D.3 construction can be evaluated even when the manuscript's extremely large numerical preconditions are not satisfied; the result then carries **no theorem-backed complexity guarantee**.
- The extension-ring Taylor precision and degree are bounded. Results are exact only in the specified truncated ring modulo `2^p`.
- Resource limits reject expensive inputs rather than returning partial results as exact.

## Usage

`veritas-eth31 construct --n 2 --clauses-json "[[1,2]]" --output cert.json`

`veritas-eth31 check --certificate cert.json`

For API access, POST `/v1/research/eth/geometric-mode-children` and replay with `/v1/research/eth/geometric-mode-children/check`.
