"""Schema validation for artifact JSON files."""

from __future__ import annotations

from typing import Any


class SchemaValidationError(Exception):
    """Raised when schema validation fails."""

    def __init__(self, message: str, field: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.field = field


def validate_tickets_schema(payload: dict[str, Any]) -> None:
    """Validate tickets.json schema per PRD Section 6.4.
    
    Raises SchemaValidationError if validation fails.
    """
    if not isinstance(payload, dict):
        raise SchemaValidationError("Tickets payload must be a dictionary")
    
    # Check epic_title
    if "epic_title" not in payload:
        raise SchemaValidationError("Missing required field: epic_title")
    if not isinstance(payload["epic_title"], str):
        raise SchemaValidationError("epic_title must be a string", field="epic_title")
    
    # Check tickets array
    if "tickets" not in payload:
        raise SchemaValidationError("Missing required field: tickets")
    if not isinstance(payload["tickets"], list):
        raise SchemaValidationError("tickets must be an array", field="tickets")
    
    tickets = payload["tickets"]
    if not tickets:
        raise SchemaValidationError("tickets array cannot be empty", field="tickets")
    
    # Validate each ticket
    required_fields = {"id", "title", "description", "acceptance_criteria", "files_expected", "risk_level", "estimate_hours"}
    valid_risk_levels = {"low", "med", "high"}
    
    for idx, ticket in enumerate(tickets):
        if not isinstance(ticket, dict):
            raise SchemaValidationError(f"tickets[{idx}] must be a dictionary", field=f"tickets[{idx}]")
        
        # Check required fields
        missing = required_fields - set(ticket.keys())
        if missing:
            raise SchemaValidationError(
                f"tickets[{idx}] missing required fields: {sorted(missing)}",
                field=f"tickets[{idx}]"
            )
        
        # Validate field types
        if not isinstance(ticket["id"], str):
            raise SchemaValidationError(f"tickets[{idx}].id must be a string", field=f"tickets[{idx}].id")
        if not isinstance(ticket["title"], str):
            raise SchemaValidationError(f"tickets[{idx}].title must be a string", field=f"tickets[{idx}].title")
        if not isinstance(ticket["description"], str):
            raise SchemaValidationError(f"tickets[{idx}].description must be a string", field=f"tickets[{idx}].description")
        
        # acceptance_criteria must be array of strings
        if not isinstance(ticket["acceptance_criteria"], list):
            raise SchemaValidationError(
                f"tickets[{idx}].acceptance_criteria must be an array",
                field=f"tickets[{idx}].acceptance_criteria"
            )
        for ac_idx, ac in enumerate(ticket["acceptance_criteria"]):
            if not isinstance(ac, str):
                raise SchemaValidationError(
                    f"tickets[{idx}].acceptance_criteria[{ac_idx}] must be a string",
                    field=f"tickets[{idx}].acceptance_criteria[{ac_idx}]"
                )
        
        # files_expected must be array of strings
        if not isinstance(ticket["files_expected"], list):
            raise SchemaValidationError(
                f"tickets[{idx}].files_expected must be an array",
                field=f"tickets[{idx}].files_expected"
            )
        for fe_idx, fe in enumerate(ticket["files_expected"]):
            if not isinstance(fe, str):
                raise SchemaValidationError(
                    f"tickets[{idx}].files_expected[{fe_idx}] must be a string",
                    field=f"tickets[{idx}].files_expected[{fe_idx}]"
                )
        
        # risk_level must be valid enum
        if ticket["risk_level"] not in valid_risk_levels:
            raise SchemaValidationError(
                f"tickets[{idx}].risk_level must be one of {valid_risk_levels}",
                field=f"tickets[{idx}].risk_level"
            )
        
        # estimate_hours must be number
        if not isinstance(ticket["estimate_hours"], (int, float)):
            raise SchemaValidationError(
                f"tickets[{idx}].estimate_hours must be a number",
                field=f"tickets[{idx}].estimate_hours"
            )
        
        # owner is optional, but if present must be string or null
        if "owner" in ticket and ticket["owner"] is not None and not isinstance(ticket["owner"], str):
            raise SchemaValidationError(
                f"tickets[{idx}].owner must be a string or null",
                field=f"tickets[{idx}].owner"
            )


def validate_evidence_map_schema(payload: dict[str, Any]) -> None:
    """Validate evidence-map.json schema per PRD Section 6.4.
    
    Raises SchemaValidationError if validation fails.
    """
    if not isinstance(payload, dict):
        raise SchemaValidationError("Evidence map payload must be a dictionary")
    
    # Check claims array
    if "claims" not in payload:
        raise SchemaValidationError("Missing required field: claims")
    if not isinstance(payload["claims"], list):
        raise SchemaValidationError("claims must be an array", field="claims")
    
    claims = payload["claims"]
    for idx, claim in enumerate(claims):
        if not isinstance(claim, dict):
            raise SchemaValidationError(f"claims[{idx}] must be a dictionary", field=f"claims[{idx}]")
        
        required_claim_fields = {"claim_id", "claim_text", "supporting_sources", "confidence"}
        missing = required_claim_fields - set(claim.keys())
        if missing:
            raise SchemaValidationError(
                f"claims[{idx}] missing required fields: {sorted(missing)}",
                field=f"claims[{idx}]"
            )
        
        # Validate claim_id
        if not isinstance(claim["claim_id"], str):
            raise SchemaValidationError(f"claims[{idx}].claim_id must be a string", field=f"claims[{idx}].claim_id")
        
        # Validate claim_text
        if not isinstance(claim["claim_text"], str):
            raise SchemaValidationError(f"claims[{idx}].claim_text must be a string", field=f"claims[{idx}].claim_text")
        
        # Validate supporting_sources
        if not isinstance(claim["supporting_sources"], list):
            raise SchemaValidationError(
                f"claims[{idx}].supporting_sources must be an array",
                field=f"claims[{idx}].supporting_sources"
            )
        
        for src_idx, source in enumerate(claim["supporting_sources"]):
            if not isinstance(source, dict):
                raise SchemaValidationError(
                    f"claims[{idx}].supporting_sources[{src_idx}] must be a dictionary",
                    field=f"claims[{idx}].supporting_sources[{src_idx}]"
                )
            
            required_source_fields = {"file", "line_range", "quote"}
            missing_src = required_source_fields - set(source.keys())
            if missing_src:
                raise SchemaValidationError(
                    f"claims[{idx}].supporting_sources[{src_idx}] missing required fields: {sorted(missing_src)}",
                    field=f"claims[{idx}].supporting_sources[{src_idx}]"
                )
            
            if not isinstance(source["file"], str):
                raise SchemaValidationError(
                    f"claims[{idx}].supporting_sources[{src_idx}].file must be a string",
                    field=f"claims[{idx}].supporting_sources[{src_idx}].file"
                )
            
            if not isinstance(source["line_range"], list) or len(source["line_range"]) != 2:
                raise SchemaValidationError(
                    f"claims[{idx}].supporting_sources[{src_idx}].line_range must be [number, number]",
                    field=f"claims[{idx}].supporting_sources[{src_idx}].line_range"
                )
            
            if not all(isinstance(x, (int, float)) for x in source["line_range"]):
                raise SchemaValidationError(
                    f"claims[{idx}].supporting_sources[{src_idx}].line_range must contain numbers",
                    field=f"claims[{idx}].supporting_sources[{src_idx}].line_range"
                )
            
            if not isinstance(source["quote"], str):
                raise SchemaValidationError(
                    f"claims[{idx}].supporting_sources[{src_idx}].quote must be a string",
                    field=f"claims[{idx}].supporting_sources[{src_idx}].quote"
                )
            
            # Validate quote length (≤18 words per PRD)
            quote_words = len(source["quote"].split())
            if quote_words > 18:
                raise SchemaValidationError(
                    f"claims[{idx}].supporting_sources[{src_idx}].quote must be ≤18 words (got {quote_words})",
                    field=f"claims[{idx}].supporting_sources[{src_idx}].quote"
                )
        
        # Validate confidence
        if not isinstance(claim["confidence"], (int, float)):
            raise SchemaValidationError(
                f"claims[{idx}].confidence must be a number",
                field=f"claims[{idx}].confidence"
            )
        if not (0 <= claim["confidence"] <= 1):
            raise SchemaValidationError(
                f"claims[{idx}].confidence must be between 0 and 1",
                field=f"claims[{idx}].confidence"
            )
    
    # Validate top_features (required)
    if "top_features" not in payload:
        raise SchemaValidationError("Missing required field: top_features")
    if not isinstance(payload["top_features"], list):
        raise SchemaValidationError("top_features must be an array", field="top_features")
    
    top_features = payload["top_features"]
    if len(top_features) != 3:
        raise SchemaValidationError(
            f"top_features must contain exactly 3 features (got {len(top_features)})",
            field="top_features"
        )
    
    for idx, feature in enumerate(top_features):
        if not isinstance(feature, dict):
            raise SchemaValidationError(f"top_features[{idx}] must be a dictionary", field=f"top_features[{idx}]")
        
        required_feature_fields = {"feature", "rationale", "linked_claim_ids"}
        missing = required_feature_fields - set(feature.keys())
        if missing:
            raise SchemaValidationError(
                f"top_features[{idx}] missing required fields: {sorted(missing)}",
                field=f"top_features[{idx}]"
            )
        
        if not isinstance(feature["feature"], str):
            raise SchemaValidationError(f"top_features[{idx}].feature must be a string", field=f"top_features[{idx}].feature")
        if not isinstance(feature["rationale"], str):
            raise SchemaValidationError(f"top_features[{idx}].rationale must be a string", field=f"top_features[{idx}].rationale")
        if not isinstance(feature["linked_claim_ids"], list):
            raise SchemaValidationError(
                f"top_features[{idx}].linked_claim_ids must be an array",
                field=f"top_features[{idx}].linked_claim_ids"
            )
        if not all(isinstance(x, str) for x in feature["linked_claim_ids"]):
            raise SchemaValidationError(
                f"top_features[{idx}].linked_claim_ids must contain strings",
                field=f"top_features[{idx}].linked_claim_ids"
            )
    
    # Validate feature_choice (optional, but if present must have correct structure)
    if "feature_choice" in payload and payload["feature_choice"] is not None:
        feature_choice = payload["feature_choice"]
        if not isinstance(feature_choice, dict):
            raise SchemaValidationError("feature_choice must be a dictionary or null", field="feature_choice")
        
        required_choice_fields = {"feature", "rationale", "linked_claim_ids"}
        missing = required_choice_fields - set(feature_choice.keys())
        if missing:
            raise SchemaValidationError(
                f"feature_choice missing required fields: {sorted(missing)}",
                field="feature_choice"
            )
        
        if not isinstance(feature_choice["feature"], str):
            raise SchemaValidationError("feature_choice.feature must be a string", field="feature_choice.feature")
        if not isinstance(feature_choice["rationale"], str):
            raise SchemaValidationError("feature_choice.rationale must be a string", field="feature_choice.rationale")
        if not isinstance(feature_choice["linked_claim_ids"], list):
            raise SchemaValidationError("feature_choice.linked_claim_ids must be an array", field="feature_choice.linked_claim_ids")
        if not all(isinstance(x, str) for x in feature_choice["linked_claim_ids"]):
            raise SchemaValidationError("feature_choice.linked_claim_ids must contain strings", field="feature_choice.linked_claim_ids")
