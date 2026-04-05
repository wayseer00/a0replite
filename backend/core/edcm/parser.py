from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Turn:
    turn_id: str
    actor_id: str
    utterances: list[dict]
    raw_text: str
    timestamp: Optional[float] = None


@dataclass
class Round:
    round_id: str
    turns: list[Turn]
    opening_actor: str


@dataclass
class ConversationStructure:
    turns: list[Turn]
    rounds: list[Round]


def parse_utterances(utterances: list[dict]) -> ConversationStructure:
    """
    Parse utterances into Turns and Rounds per the edcmbone spec.
    - Merge consecutive same-actor utterances into one Turn (UNK actors are never merged).
    - Turn IDs: t0000, t0001, …
    - Round: starts at the first turn of that round's opening_actor; ends just before
      that same actor's NEXT occurrence. Each new round's opening_actor is determined
      fresh from the actor of the first turn in that round — NOT fixed globally.
    """
    if not utterances:
        return ConversationStructure(turns=[], rounds=[])

    turns = _build_turns(utterances)
    rounds = _build_rounds(turns)
    return ConversationStructure(turns=turns, rounds=rounds)


def _build_turns(utterances: list[dict]) -> list[Turn]:
    turns: list[Turn] = []
    turn_idx = 0
    i = 0

    while i < len(utterances):
        utt = utterances[i]
        actor = utt.get("actor_id", "UNK")
        raw = utt.get("raw_text", "")
        ts = utt.get("timestamp")

        if actor == "UNK":
            turns.append(
                Turn(
                    turn_id=f"t{turn_idx:04d}",
                    actor_id="UNK",
                    utterances=[utt],
                    raw_text=raw,
                    timestamp=ts,
                )
            )
            turn_idx += 1
            i += 1
            continue

        merged_utts = [utt]
        merged_text = raw
        j = i + 1
        while j < len(utterances):
            next_utt = utterances[j]
            next_actor = next_utt.get("actor_id", "UNK")
            if next_actor == actor and next_actor != "UNK":
                merged_utts.append(next_utt)
                merged_text = merged_text + " " + next_utt.get("raw_text", "")
                j += 1
            else:
                break

        turns.append(
            Turn(
                turn_id=f"t{turn_idx:04d}",
                actor_id=actor,
                utterances=merged_utts,
                raw_text=merged_text.strip(),
                timestamp=ts,
            )
        )
        turn_idx += 1
        i = j

    return turns


def _build_rounds(turns: list[Turn]) -> list[Round]:
    """
    Build rounds where each round's opening_actor is determined from the FIRST TURN
    of that round. A round ends when its opening_actor appears again (the next
    occurrence of that actor starts a new round).

    This means:
    - Round 0 opens with turns[0].actor_id (e.g. "user")
    - Round 0 ends just before the next occurrence of "user"
    - Round 1 opens with whoever starts it (which may be "user" again or "assistant")
    """
    if not turns:
        return []

    rounds: list[Round] = []
    round_idx = 0
    start_i = 0

    while start_i < len(turns):
        opening_actor = turns[start_i].actor_id

        end_i = start_i + 1
        while end_i < len(turns):
            if turns[end_i].actor_id == opening_actor:
                break
            end_i += 1

        round_turns = turns[start_i:end_i]
        rounds.append(
            Round(
                round_id=f"r{round_idx:04d}",
                turns=round_turns,
                opening_actor=opening_actor,
            )
        )
        round_idx += 1
        start_i = end_i

    return rounds
