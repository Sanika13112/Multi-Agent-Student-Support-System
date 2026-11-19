
"""
Multi-Agent Student Support System

Hybrid Supervisor Agent

Combines rule-based routing and LLM-based routing.

Stage 1: Rule-based routing is attempted first.
Stage 2: Qwen2.5 LLM handles queries not classified by rules.
Stage 3: Final routing decision is returned.
"""

from agents.supervisor.rule_router import rule_based_router
from agents.supervisor.llm_router import llm_based_router


def create_routing_response(
    success,
    intent="unknown",
    agent=None,
    confidence=0.0,
    method=None,
    message=None
):
    """
    Create a consistent routing response.
    """

    response = {
        "success": success,
        "intent": intent,
        "agent": agent,
        "confidence": confidence,
        "method": method
    }

    if message:
        response["message"] = message

    return response


def validate_routing_result(result):
    """
    Validate the result returned by a routing method.
    """

    if not isinstance(result, dict):
        raise ValueError("Invalid routing response.")

    intent = result.get("intent")
    agent = result.get("agent")

    if not intent or intent == "unknown":
        raise ValueError("Unable to identify query intent.")

    if not agent:
        raise ValueError("No suitable agent was identified.")

    try:
        confidence = float(result.get("confidence", 0.0))
    except (TypeError, ValueError):
        confidence = 0.0

    # Keep confidence within the valid range.
    confidence = max(0.0, min(1.0, confidence))

    return {
        "intent": intent,
        "agent": agent,
        "confidence": confidence
    }


def route_student_query(message):
    """
    Route a student query using hybrid intelligence.

    Args:
        message (str): Student's input query.

    Returns:
        dict: Final routing decision containing:
            success, intent, agent, confidence, method.
    """

    # =====================================
    # STEP 1: VALIDATE INPUT
    # =====================================

    if not isinstance(message, str) or not message.strip():

        return create_routing_response(
            success=False,
            message="Please enter a valid question."
        )

    message = message.strip()

    # =====================================
    # STEP 2: RULE-BASED ROUTING
    # =====================================

    try:

        rule_result = rule_based_router(message)

        if isinstance(rule_result, dict):

            if rule_result.get("intent") != "unknown":

                validated_result = validate_routing_result(
                    rule_result
                )

                return create_routing_response(
                    success=True,
                    intent=validated_result["intent"],
                    agent=validated_result["agent"],
                    confidence=validated_result["confidence"],
                    method="rule_based"
                )

    except Exception:
        # Continue to LLM routing if rule routing fails.
        pass

    # =====================================
    # STEP 3: LLM-BASED ROUTING
    # =====================================

    try:

        llm_result = llm_based_router(message)

        validated_result = validate_routing_result(
            llm_result
        )

        return create_routing_response(
            success=True,
            intent=validated_result["intent"],
            agent=validated_result["agent"],
            confidence=validated_result["confidence"],
            method="llm"
        )

    except Exception:

        return create_routing_response(
            success=False,
            intent="unknown",
            agent=None,
            confidence=0.0,
            method="llm",
            message="Unable to classify the query. Please try again."
        )
