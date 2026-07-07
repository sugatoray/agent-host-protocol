# Check with prompt

Register /ctdw as a custom command. It is defined below.

## COMMAND

/ctdw: add a custom command for running the following prompt.

TARGET_FOLDER: clients/python

## COMMAND-BODY

Update SPEC.md, GAPANALYSIS.md (and GAPCONTEXT.md), HANDOFF.md and add/update a file WISDOM.md under {{ TARGET_FOLDER }} folder. WISDOM.md will contain project specific:

- "Constraints: Respect and conform to them"
- "Traps: Avoid them always"
- "Ditches: Bad patterns or decisions to
  avoid"
- "Wisdom: Best practices to adopt within the python client along-with Red/Green TDD"

> NOTE: GAPANALYSIS.md provides _what?_ and GAPCONTEXT.md provides _why?_ for each gap. Once a gap is closed, update the GAPCONTEXT.md first with marking that specific GAP as CLOSED. Once it is committed, then in the second pass, update the GAPCONTEXT.md to remove the closed gap from the list of open GAPs and update the SPEC.md file accordingly with the closed GAP.

## CHANGELOG

Finally update CHANGELOG.md with summary briefings of the updates made.
