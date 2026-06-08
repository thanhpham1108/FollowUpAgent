# -------------------------------------------------------
# tests/test_analyze.py
# Test cho endpoint POST /api/v1/candidates/analyze
# -------------------------------------------------------
# Test cases:
#   - test_analyze_returns_202       : Request hợp lệ → 202 Accepted
#   - test_analyze_missing_ssn       : Thiếu SSN → 422
#   - test_analyze_missing_name      : Thiếu candidate_name → 422
#   - test_analyze_invalid_url       : URL không hợp lệ → 422
#   - test_analyze_empty_body        : Body rỗng → 422
#
# TODO: Implement test cases
# -------------------------------------------------------
