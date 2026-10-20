# Crypto-agility for legacy objects

**Support, references, coverage, and transition authority**

Arifa Khan · 20 October 2026 · version 0.3.0

## Abstract

Support for a successor cryptographic algorithm does not establish that existing
protected objects can complete a migration. This note separates four assessment
questions: successor support, authorization-reference mutability, legacy-object
coverage, and transition authority. It gives a counting identity for the share
not successfully transitioned within a fixed assessed population. Mutable
references can permit key replacement without relocating assets; they do not
alone authorize updates for inactive controllers. The accompanying code checks
declared inputs and performs bookkeeping. It does not measure a live system,
verify outcomes, establish completeness, or implement a migration protocol.

## Context and contribution

[NIST CSWP 39-upd1][nist] already addresses discovery, inventory, governance and
migration. This note applies those concerns to persistent authorization over
outstanding objects. It does not claim to originate crypto-agility assessment or
to provide a newly discovered mathematical result.

Reference mutability and authority to update are distinct questions. They are
not demonstrated independent variables. Authority availability, operational
execution, coverage and successful retirement of predecessor authority can each
limit migration. An authorized path that never executes is not a success.

## Four assessment questions

Report these with an explicit population, snapshot, deadline and weighting.
The implementation stores that scope as caller-supplied text; it does not
verify the inventory or chronology. Do not average away a missing capability.

| Dimension | Question | Qualification |
|---|---|---|
| A_M: mechanism support | Can relevant paths use the successor? | Distinguish proposed, implemented, activated and operationally supported. Activation alone does not prove all endpoints support it. |
| A_R: reference mutability | Can the protected object's authorization change while its primary identity persists? | State who can make the change and what still depends on the predecessor. |
| A_C: coverage | What relevant objects and paths are known and reachable? | Discovery, reachability and completeness differ. The code reports declared record coverage only. |
| A_T: transition authority | Who may transition objects, including without incumbent cooperation? | Availability does not imply successful execution. State the actual governance and operational assumptions. |

## A conditional residual identity

Fix a nonempty population U at a snapshot, a deadline t and positive total
weight. Use object, value or authority-path weights consistently. Freeze value
weights at the snapshot; do not mix changing valuations or denominators. Each
object's selected weight is nonnegative.

Let r be the fraction of the assessed weight successfully transitioned through
incumbent-controller action by t. Allocate those successes first. Let q be the
fraction of the **remaining weight** successfully transitioned through a path
authorized independently of that incumbent. Count overlapping capabilities
only once: q excludes objects already allocated to r.

Then the fraction **not successfully transitioned** is:

> R = (1 − r)(1 − q).

This follows by partitioning the population. It needs no independence assumption
and makes no empirical prediction about r or q. If r = 1, R = 0 and q is
undefined on the empty remainder; the implementation uses q = 0 as its canonical
input convention. For an empty assessed population, the amount is zero and the
fraction is undefined (`None`), rather than evidence of successful migration.

Success means the declared continuity objective is satisfied and predecessor
authority is retired wherever required. Merely responding or attempting an
update does not count. Adding a new key while leaving an unsafe authorization
path usable is not sufficient where the objective requires that path's removal.

* If no independent successful path serves the remainder, q = 0 and R = 1 − r.
* If one succeeds for the whole remainder, q = 1 and R = 0.
* A mutable reference alone establishes neither q nor R.

Holding r and q fixed, reference mutability does not appear in this identity.
That is **not** a causal finding that architecture cannot improve migration:
mutability may affect achievable success, cost, throughput, timing and risk.

### Three outcomes, with a residual label

| Outcome | Meaning |
|---|---|
| Transitioned | The declared continuity and security objectives are satisfied. |
| Disabled | Predecessor authority is stopped, but required continuity is not restored. |
| Unresolved | Neither of those outcomes is established; this includes unknown status. |

These are disjoint bookkeeping categories at the deadline, not inferred
operational states. **R includes both disabled and unresolved weight.** It must
not be labelled solely “unresolved,” and is not a measure of remaining vulnerable
authority: a fully disabled population can have R = 1.

The optional `disabled_fraction` is over the **whole** assessed weight, not the
remainder. It must be at most R. If it is omitted, the disabled/unresolved split
is unknown. The code keeps it unknown rather than treating all residual objects
as exposed. A full security assessment needs more than these three categories.

## Object continuity is not downstream compatibility

In an ordinary Bitcoin migration, legacy outputs are consumed and successor
outputs created. A spent outpoint is no longer spendable, but its historical
reference remains meaningful. Wallets and applications may follow transactions
or use their own stable identifiers. It is wrong to say every external reference
is invalidated.

An account-level key rotation can preserve an account identifier, but key-pinned
clients, sessions, proofs, indexes or integrations may still need updates. The
rotation also changes ledger state and can produce records. It is wrong to say
that preserving the account breaks nothing or creates nothing.

The code therefore reports primary object continuity and leaves dependent
breakage **undetermined**. It does not infer a blast-radius metric from identity.

## Bitcoin and NEAR: limited architectural illustrations

Bitcoin supports multiple output and script forms. Ordinary changes in spending
conditions involve spending into suitable successor outputs. [BIP-360][bip360]
is a draft proposal as checked for this note, not a deployed comprehensive
post-quantum migration or proof that every desired scheme is a trivial upgrade.

NEAR supports mutable access-key sets and ML-DSA-65 account keys. Through the
ordinary transaction path, a full-access key can add or remove keys. Contract
logic can also issue key-management actions; whether a recovery or delegated
path is usable depends on the account's configuration. Consequently, losing
one key does not establish that every possible update path is lost, and having
mutable keys does not establish an independent recovery path. See [NEAR access
keys][near-keys], [contract actions][near-actions] and [NEP-645][nep645].

The useful contrast is the primary-object update structure. Neither architecture
alone establishes migration of inactive accounts, every outstanding object, or
every consensus, contract and cross-chain dependency. No live-system scores or
population estimates are presented here.

## Implementation and reproducibility

Python 3.10+; standard library only. Run from the repository directory:


python3 -I test_agility.py


The tests explicitly add their own directory to the import path so this flat
repository works with `-I`. That flag alone is not proof of isolation. Inspect
and test only the intended files in a fresh directory when checking provenance.

`Assessment` is an immutable record. Capability labels describe the same
configuration throughout the declared scenario window. If capabilities changed
over that period, split the analysis into suitable populations/windows or use a
richer model; do not mix today's “no authority” label with earlier successes.
Invalid or contradictory inputs raise `ValueError` at construction.

Numeric inputs may be `int`, finite `float`, or `fractions.Fraction`; booleans
are rejected. A float is interpreted via its shortest decimal string. For exact
ratios or very small tails, supply `Fraction`. Already-rounded input data cannot
be recovered. Methods use rational arithmetic without rounding away residuals.

`residual_amount()` returns an exact `Fraction` in the declared units. For object
weighting, `residual_count()` returns an integer only when the computed object
equivalents are integral; otherwise it raises. For other weightings it raises
because a value/path fraction cannot establish an object count. Even an integral
result from assumed inputs is not an observed count.

Value/path weighting requires an explicit total `weight_known` and `weight_unit`.
Record coverage remains separate from weight coverage, which is not computed.
A believed total is a caller assertion, not a completeness certificate; 100%
declared record coverage does not prove the real universe was discovered.

`report()` is JSON-safe: fractions and amounts are **ratio strings** such as
`"1/5"`, `"100"` or `"200/3"`, and undefined values are `None`. Parse ratio strings
with `Fraction` if numeric operations are needed. Comparison helpers return
`Fraction` values directly; they are not the JSON report interface.

```python
from agility import Assessment, MechanismSupport

a = Assessment(
    system="synthetic example",
    scope="one billion fixed records; snapshot and deadline 2026-10-20",
    evaluated_at="2026-10-20",
    mechanism=MechanismSupport.ACTIVATED,
    population_known=1_000_000_000,
    r_incumbent=0.9999999,
    assumptions=("r is assumed, not observed",),
)
assert a.residual_count() == 100
assert a.report()["not_transitioned_fraction"] == "1/10000000"
```

The synthetic tests include explicit success-set complements over finite
populations and heterogeneous weights, tiny residuals, contradictory inputs,
outcome partitions and units. They are not empirical “ground truth” about a chain.

Three helpers illustrate the arithmetic:

* `authority_effect`: changes availability while holding r and q fixed. An
  unused independent path does not change the achieved residual.
* `independent_success_effect`: varies assumed q with availability fixed. Each
  returned row carries its success assumption.
* `continuity_effect`: changes primary continuity with r and q fixed. The
  identity is unchanged; downstream compatibility is not inferred.

These are sensitivities of a definition, not controlled real-world experiments.

### Changes from 0.2.0

Version 0.3.0 intentionally tightens the API: it rejects contradictory successes,
invalid totals and unsupported types; uses exact rational values; refuses rounded
or value-derived object counts; distinguishes empty denominators; represents the
optional disabled/unresolved split; and changes report keys/types accordingly.
It removes automatic downstream-breakage predictions and corrects the comparison
helpers. There is no scalar agility score and no additional executable module.

## Limitations and earlier correction

An earlier draft incorrectly treated mutable references as eliminating holder
action and mixed authority availability with assumed execution success. That
claim is withdrawn. Reviewers identified the distinction; regression cases now
cover it. The revised note makes no universal zero-residual claim.

This diagnostic does not discover objects, verify evidence, prove completeness,
enforce policy, recover keys, retire credentials or implement any migration
mechanism. It does not originate a validated predictive metric. No claim of
novelty or patent clearance follows from its publication.

## Licence and citation

README.md: [CC BY 4.0][ccby], with attribution and the other applicable terms.
agility.py, test_agility.py and CITATION.cff: MIT. See `LICENSE`.
`CITATION.cff` supplies citation metadata; it does not mint a DOI. No DOI is
claimed for this release candidate.

[nist]: https://csrc.nist.gov/pubs/cswp/39/upd1/considerations-for-achieving-crypto-agility/final
[near-keys]: https://docs.near.org/protocol/accounts-contracts/access-keys
[near-actions]: https://docs.near.org/smart-contracts/anatomy/actions
[nep645]: https://github.com/near/NEPs/blob/master/neps/nep-0645.md
[bip360]: https://github.com/bitcoin/bips/blob/master/bip-0360.mediawiki
[ccby]: https://creativecommons.org/licenses/by/4.0/
