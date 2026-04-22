# Carrier Error Code Reference

## Error 402 — Invalid Zip Code
The zip code submitted does not match USPS 5-digit format. Cross-reference internal HR record and resubmit with corrected zip.

## Error 415 — Missing or Malformed Date of Birth
A dependent date of birth is blank or fails YYYY-MM-DD validation. Cross-reference HR dependent records and resubmit with corrected date.

## Error 501 — Duplicate Enrollment
This employee ID was already submitted in the current enrollment window. Check for duplicate records before resubmitting.

## Error 308 — Invalid Plan Code
The plan code submitted does not match any active carrier plan for this group. Verify plan codes against the current carrier contract.

## Error 610 — SSN Format Error
The Social Security Number field is malformed or contains non-numeric characters. SSN last 4 must be exactly 4 digits.

## Error 209 — Invalid Coverage Tier
The coverage tier submitted does not match the dependent enrollment records on file. Valid tiers: EE_ONLY, EE_SPOUSE, EE_PLUS_CHILDREN, EE_PLUS_ONE, FAMILY. Cross-reference dependents in the HR record to determine the correct tier.

## Error 716 — Enrollment Window Expired
The enrollment submission date exceeds the 60-day qualifying life event (QLE) window. Carriers require enrollment to be submitted within 60 days of the qualifying event (birth, marriage, loss of other coverage, etc.). A carrier exception request must be filed to proceed outside this window.
