# E4 user study plan (draft, 1 November 2026)

Status: DRAFT for Aftab and Dr Rimsha Anam to approve. Items in [square brackets] are not decided yet.

## Question the study answers

Can a person who has never seen Airlume get a correct answer about Lahore's air quality by typing a question in English or Roman Urdu, and how long does it take? This is evaluation E4 in the plan. It is a usability study, not a measure of the model (that is the benchmark).

## Who and how many

8 to 10 participants, none of them the three team members. Classmates, family or friends who read English or Roman Urdu. Target at least 4 who write Roman Urdu by habit, because 60 percent of the questions classmates wrote were Roman Urdu. Convenience sample: say so in the report, and do not claim it represents the public.

## Session (about 15 minutes, one person at a time)

1. Read the consent line below, get a yes. (1 min)
2. No demo. Say only: "This is a website that answers questions about air quality. Please do these three things in your own words." (1 min)
3. Three tasks, one at a time, observer silent unless the participant is stuck for 90 seconds. (8 min)
4. System Usability Scale, 10 questions, on paper or a form. (3 min)
5. Two open questions: "What was confusing?" and "What would you have asked that it could not answer?" (2 min)

## The three tasks

Tasks are worded as goals, not as questions to type, so the participant has to find the words.

| Task | Goal given to the participant | What counts as success |
|---|---|---|
| T1 current | "Find out which part of Lahore has the worst air right now." | The answer names the station the app shows as worst at that moment. Observer checks the map. |
| T2 comparison | "Find out whether Gulberg is better or worse today than yesterday." | The answer states the direction that matches the stored numbers for both windows. Observer checks the two values. |
| T3 decision, Roman Urdu or English by preference | "You want to go for a walk this evening. Find out if the air allows it." | The answer gives a forecast or current band with its published advice and the participant can say, in their own words, what it told them. |

Ground truth for T1 and T2 is read from the app's own store at the time of the session and written on the recording sheet before the participant starts, so a stale map cannot make a correct answer look wrong.

## What is recorded per participant per task

Anonymous id (P01, P02, ...), language used, the exact text typed, time from first keystroke to an answer on screen, whether the answer was correct (yes or no, against the ground truth above), whether the participant needed the observer, number of times the app asked a clarifying question, number of reworded retries, and any error message shown. Template: `docs/study/e4-recording-sheet.csv`.

## Measures and how they are reported

- **Task success:** correct without help, as correct/n with a 95 percent Wilson interval, per task and pooled. With 8 to 10 people one failure moves the figure by 10 points: report counts first.
- **Time to answer:** median and range per task, not the mean. Small n, skewed times.
- **System Usability Scale:** standard scoring. For items 1, 3, 5, 7, 9 take the answer minus 1; for items 2, 4, 6, 8, 10 take 5 minus the answer; add the ten values and multiply by 2.5, giving 0 to 100 per person. Report the mean with a bootstrap interval and the n. A SUS score from 8 to 10 people is indicative only.
- **Roman Urdu versus English:** report separately, with counts, no test of significance at this n.
- **Open comments:** quote, group by theme, count themes.

## The SUS statements (answer 1 strongly disagree to 5 strongly agree)

1. I think that I would like to use this system frequently.
2. I found the system unnecessarily complex.
3. I thought the system was easy to use.
4. I think that I would need the support of a technical person to be able to use this system.
5. I found the various functions in this system were well integrated.
6. I thought there was too much inconsistency in this system.
7. I would imagine that most people would learn to use this system very quickly.
8. I found the system very cumbersome to use.
9. I felt very confident using the system.
10. I needed to learn a lot of things before I could get going with this system.

(Brooke 1996. Wording kept as published; change "system" to "website" only if participants stumble on it, and note the change.)

## Consent line, read aloud

"I am testing a website, not you. I will note what you type, how long it takes and your answers to a few questions. I will not record your name, voice or face, and nothing you say will be linked to you. You can stop at any time. Is that all right?"

Record yes or no on the sheet. No names, no contact details, no photographs, no screen recording that shows anyone's face.

## Where it runs

On the laptop with `run.bat` (public deploy is not done yet): [confirm the study runs on the same build that will be deployed]. Use a fixed question limit so the Groq daily budget is not spent by the study: each participant types about 5 to 15 questions, so 10 participants is about 150 questions at most. [Check the remaining Groq budget on the day.] If the model is unreachable the app falls back to the rule-based stub; note that on the sheet, because it changes what is being tested.

## Schedule

- By 3 Nov: Aftab and supervisor approve this plan; book sessions.
- 4 to 8 Nov: sessions, two or three a day.
- 9 to 10 Nov: tidy the sheet, compute the figures, write the results section.
Needs: one quiet room, the laptop on mains power (the collector task is sensitive to battery mode), a phone timer, printed SUS form.

## Limits to state in the report

Small convenience sample. Observer present, which inflates success a little. One build, one week, smog season only. Ground truth is the app's own stored data, so the study tests whether people can read the answer, not whether the data are right (that is the validation work).

## Open items

- [Supervisor approval of consent wording and sample.]
- [Whether the university needs a formal ethics sign-off for a non-clinical usability study of this size.]
- [Who observes: one of the team, with a second person timing if possible.]
