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
    Parse utterances into Turns and Rounds.
    - Merge consecutive same-actor utterances into one Turn (UNK actors never merged).
    - Turn IDs: t0000, t0001, ...
    - Round: starts at actor X's turn; ends just before X's next turn. If X never speaks again, ends at last turn.
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
    if not turns:
        return []

    rounds: list[Round] = []
    round_idx = 0
    opening_actor = turns[0].actor_id

    start_i = 0
    for i in range(1, len(turns)):
        if turns[i].actor_id == opening_actor:
            round_turns = turns[start_i:i]
            rounds.append(
                Round(
                    round_id=f"r{round_idx:04d}",
                    turns=round_turns,
                    opening_actor=opening_actor,
                )
            )
            round_idx += 1
            start_i = i

    final_round = turns[start_i:]
    if final_round:
        rounds.append(
            Round(
                round_id=f"r{round_idx:04d}",
                turns=final_round,
                opening_actor=final_round[0].actor_id,
            )
        )

    return rounds
